"""Import verified official audio copies into the local evaluation collection.

No transcript is indexed as evidence. Keep recordings out of public source bundles;
see docs/AUDIO_SOURCES.md for the source's reproduction conditions.
"""
import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.db import ROOT, DATA, connect, init_db, job


def validate(path, item):
    if path.stat().st_size != item['size_bytes']:
        raise ValueError(f"Size mismatch: {path.name}")
    with path.open('rb') as stream:
        checksum = hashlib.file_digest(stream, 'sha256').hexdigest()
    if checksum != item['sha256']:
        raise ValueError(f"Checksum mismatch: {path.name}")
    import av
    with av.open(str(path)) as media:
        if not media.streams.audio:
            raise ValueError(f"No audio stream: {path.name}")
        if abs(media.duration / av.time_base - item['duration_seconds']) > 1:
            raise ValueError(f"Unexpected duration: {path.name}")


def obtain(item, allow_download):
    destination = DATA / 'originals' / (item['id'] + '.' + item['format'])
    if destination.exists():
        validate(destination, item)
        return destination
    candidate = (ROOT / item['candidate_path']).resolve()
    if not candidate.is_relative_to(ROOT / 'work/audio-candidates'):
        raise ValueError('Candidate path is outside the research folder')
    temporary = destination.with_suffix(destination.suffix + '.part')
    try:
        if candidate.exists():
            validate(candidate, item)
            shutil.copyfile(candidate, temporary)
        elif allow_download:
            import httpx
            url = item['download_url']
            if urlparse(url).scheme != 'https' or urlparse(url).hostname != 'web.archive.org':
                raise ValueError('Only the manifest’s HTTPS archival URLs are supported')
            with httpx.stream('GET', url, follow_redirects=True, timeout=90) as response:
                response.raise_for_status()
                if response.url.scheme != 'https':
                    raise ValueError('Refusing a non-HTTPS archival redirect')
                received = 0
                with temporary.open('wb') as stream:
                    for block in response.iter_bytes():
                        received += len(block)
                        if received > item['size_bytes']:
                            raise ValueError('Download exceeds the verified file size')
                        stream.write(block)
        else:
            raise FileNotFoundError(f"Missing verified local copy: {candidate}. Use --download to fetch the public archival copy for local evaluation.")
        validate(temporary, item)
        temporary.replace(destination)
        return destination
    finally:
        if temporary.exists():
            temporary.unlink()


def playback_copy(path):
    """Decode only audio to a standard MP3; retain the unmodified source MP4."""
    if path.suffix.lower()!='.mp4':return path
    import av
    target=path.with_suffix('.playback.mp3')
    if target.exists():return target
    with av.open(str(path)) as original,av.open(str(target),'w') as output:
        stream=output.add_stream('libmp3lame',rate=44100);stream.layout='mono';stream.bit_rate=128000
        resampler=av.AudioResampler(format='fltp',layout='mono',rate=44100)
        for frame in original.decode(audio=0):
            for resampled in resampler.resample(frame):
                resampled.pts=None
                for packet in stream.encode(resampled):output.mux(packet)
        for resampled in resampler.resample(None):
            resampled.pts=None
            for packet in stream.encode(resampled):output.mux(packet)
        for packet in stream.encode(None):output.mux(packet)
    return target


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--download', action='store_true', help='Download missing archival evaluation copies over HTTPS')
    args = parser.parse_args()
    manifest = json.loads((ROOT / 'sources/audio.json').read_text(encoding='utf-8'))
    init_db()
    items = manifest['items']
    with connect() as connection:
        for item in items:
            existing = connection.execute('SELECT category FROM documents WHERE id=?', (item['id'],)).fetchone()
            if existing and existing['category'] != 'audio':
                raise ValueError('Audio identifier collides with a non-audio document')
    paths = {item['id']: playback_copy(obtain(item, args.download)) for item in items}
    columns = ['id', 'title', 'category', 'language', 'date', 'year', 'authors', 'description', 'source_label', 'source_url', 'file_path', 'checksum', 'format', 'page_count', 'summary', 'summary_kind', 'key_points', 'processing_status', 'group_key']
    placeholders = ','.join('?' for _ in columns)
    updates = ','.join(f'{column}=excluded.{column}' for column in columns if column != 'id')
    with connect() as connection:
        before = connection.execute("SELECT count(*) FROM documents WHERE category<>'audio'").fetchone()[0]
        for item in items:
            seconds = round(item['duration_seconds'])
            duration = f'{seconds // 60}m {seconds % 60:02d}s'
            description = (
                f"{item['description']} Recording type: {item['recording_kind']}. Duration: {duration}. "
                f"Provenance: official Dr. Ambedkar Foundation gallery, archived {item['wayback_timestamp'][:4]}-"
                f"{item['wayback_timestamp'][4:6]}-{item['wayback_timestamp'][6:8]}; retrieved {manifest['retrieved_at']}. "
                f"Archived original: {item['download_url']}. Local evaluation copy; reproduction permission has not been cleared."
            )
            values = {**item, 'date': item.get('date') or '', 'year': int(item['date'][:4]) if item.get('date') else None,
                      'description': description, 'file_path': str(paths[item['id']].resolve()), 'checksum': hashlib.sha256(paths[item['id']].read_bytes()).hexdigest(), 'format':paths[item['id']].suffix.lstrip('.'),
                      'page_count': 0, 'key_points': json.dumps(item['key_points'], ensure_ascii=False),
                      'processing_status': 'ready', 'group_key': item['id']}
            connection.execute(f"INSERT INTO documents({','.join(columns)}) VALUES({placeholders}) ON CONFLICT(id) DO UPDATE SET {updates}", [values[column] for column in columns])
            connection.execute('''INSERT INTO summaries(document_id,language,summary,key_points,kind,citations)
                VALUES(?,?,?,?,?,?) ON CONFLICT(document_id,language) DO UPDATE SET
                summary=excluded.summary,key_points=excluded.key_points,kind=excluded.kind,citations=excluded.citations''',
                (item['id'], 'en', item['summary'], values['key_points'], 'Curated source overview', '[]'))
        after = connection.execute("SELECT count(*) FROM documents WHERE category<>'audio'").fetchone()[0]
        if after != before:
            raise RuntimeError('Non-audio collection count changed during import')
    job('audio-import', 'complete', f'Imported {len(items)} official archival audio copies for local evaluation; one historical excerpt and two narrated works.')
    print(json.dumps({'imported': [item['id'] for item in items], 'non_audio_documents_unchanged': before}, indent=2))


if __name__ == '__main__':
    main()
