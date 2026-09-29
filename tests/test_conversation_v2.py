import json,os,tempfile
from pathlib import Path
from unittest.mock import patch
from services import conversation,narration,translation
from app import db,retrieval

HIT={'id':1,'document_id':'test','title':'Test source','category':'writings','page':7,'text':'Constitutional morality is not a natural sentiment. It has to be cultivated.'}

def test_greeting_uses_llm_without_archive_search():
    conversation.social_reply.cache_clear()
    with patch.object(conversation.llm,'generate',return_value='Hello! I’m DHAROHAR, your AI guide to Ambedkar.'),patch.object(retrieval,'search') as search:
        result=conversation.answer('Hello')
    search.assert_not_called();assert result['grounding']['status']=='social';assert result['citations']==[]

def test_unrelated_request_is_redirected_without_retrieval():
    with patch.object(conversation.llm,'generate',return_value=json.dumps({'kind':'off_topic','reply':'Please ask me about B. R. Ambedkar.'})),patch.object(retrieval,'search') as search:
        result=conversation.answer('Give me a pizza recipe')
    search.assert_not_called();assert result['grounding']['status']=='off_topic'

def test_generated_source_numbers_are_replaced_by_valid_ids():
    outputs=[{'paragraphs':[{'text':'Constitutional morality needs practice. [99, 87]','evidence':[1]}]},{'question_supported':True,'checks':[{'paragraph_id':0,'reason':'A direct explanation of cultivation.','supported':True}]}]
    with patch.object(retrieval,'search',return_value=[HIT]),patch.object(conversation.llm,'generate',side_effect=[json.dumps(x) for x in outputs]):result=conversation.answer('Explain constitutional morality')
    assert '[99]' not in result['answer'];assert result['answer'].endswith('[1]');assert result['citations'][0]['quote']==HIT['text']
    assert '87' not in result['answer']

def test_partial_support_does_not_display_rejected_paragraph():
    outputs=[{'paragraphs':[{'text':'It must be cultivated.','evidence':[1]},{'text':'It was invented in 1922.','evidence':[1]}]},{'question_supported':True,'checks':[{'paragraph_id':0,'reason':'Supported.','supported':True},{'paragraph_id':1,'reason':'Date absent.','supported':False}]}]
    with patch.object(retrieval,'search',return_value=[HIT]),patch.object(conversation.llm,'generate',side_effect=[json.dumps(x) for x in outputs]):result=conversation.answer('Explain constitutional morality')
    assert '1922' not in result['answer'];assert len(result['citations'])==1

def test_absence_of_evidence_is_not_presented_as_a_cited_fact():
    draft={'paragraphs':[{'text':'There is no evidence that Ambedkar invented the internet.','evidence':[1]}]}
    with patch.object(retrieval,'search',return_value=[HIT]),patch.object(conversation.llm,'generate',return_value=json.dumps(draft)) as generate:
        result=conversation.answer('Did Ambedkar invent the internet?')
    assert result['grounding']['status']=='insufficient';assert result['citations']==[];generate.assert_called_once()

def test_irrelevant_sources_cannot_support_an_answer_even_if_paraphrase_passes():
    outputs=[{'paragraphs':[{'text':'Constitutional morality must be cultivated.','evidence':[1]}]},{'question_supported':False,'checks':[{'paragraph_id':0,'reason':'Accurate paraphrase, unrelated question.','supported':True}]}]
    with patch.object(retrieval,'search',return_value=[HIT]),patch.object(conversation.llm,'generate',side_effect=[json.dumps(x) for x in outputs]):
        result=conversation.answer('Did Ambedkar invent the internet?')
    assert result['grounding']['status']=='insufficient';assert result['citations']==[]

def test_missing_question_support_verdict_fails_closed():
    outputs=[{'paragraphs':[{'text':'Constitutional morality needs practice.','evidence':[1]}]},{'checks':[{'paragraph_id':0,'reason':'Paraphrase.','supported':True}]}]
    with patch.object(retrieval,'search',return_value=[HIT]),patch.object(conversation.llm,'generate',side_effect=[json.dumps(x) for x in outputs]):
        result=conversation.answer('Explain constitutional morality')
    assert result['grounding']['status']=='insufficient';assert result['citations']==[]

def test_ambedkar_cast_is_resonant_and_female_title_takes_precedence():
    assert narration.cast('The Honourable Dr. B. R. Ambedkar')=='strong'
    assert narration.cast('Shrimati Hansa Mehta')=='female'
    assert narration.cast('Mrs. Ambedkar')=='female'
    assert narration.voice_name('hi','Shrimati Hansa Mehta')=='hi_IN-priyamvada-medium'

def test_unknown_person_is_not_gender_inferred_from_arbitrary_name():
    assert narration.cast('Unidentified speaker','warm')=='female' # Default narrator profile, not inferred identity.
    assert narration.cast('Unidentified speaker','clear')=='male'

def test_narration_removes_citation_markers():
    assert narration.clean_speech('An explanation. [1] [2]')=='An explanation.'

def test_unknown_translator_gender_does_not_use_narrator_default():
    assert narration.known_gender('Session text') is None
    assert narration.known_gender('An unidentified person') is None
    assert narration.known_gender('Dr. B. R. Ambedkar')=='Male'
    assert narration.known_gender('Shrimati Hansa Mehta')=='Female'

def test_translation_carries_the_right_speaker_across_segments():
    with patch.object(translation,'translate_segment',side_effect=lambda text,src,tgt,speaker:text) as segment:
        text='A long sentence. '*200
        result=translation.translate_many([text,'A second statement.'],'en','hi',['Mr. President','Shrimati Hansa Mehta'])
    assert len(result)==2
    assert segment.call_args_list[-1].args[3]=='Shrimati Hansa Mehta'
    assert all(call.args[3]=='Mr. President' for call in segment.call_args_list[:-1])

def test_translation_segments_do_not_drop_text_or_exceed_limit():
    text=('This is a complete sentence. '*200).strip()
    parts=translation.segments(text)
    assert all(len(p)<=1800 for p in parts)
    assert ' '.join(parts)==text

def test_translation_cache_avoids_second_provider_call():
    with tempfile.TemporaryDirectory() as tmp,patch.object(db,'DATA',Path(tmp)),patch.dict(os.environ,{'TRANSLATION_PROVIDER':'local'}):
        db.init_db()
        with patch.object(translation.llm,'translate',return_value='नमस्ते') as generate:
            assert translation.translate_many(['Hello'],'en','hi')==['नमस्ते']
            assert translation.translate_many(['Hello'],'en','hi')==['नमस्ते']
            generate.assert_called_once()

def test_same_language_uses_no_provider():
    with patch.object(translation.llm,'translate') as generate:
        assert translation.translate_many(['Hello'],'en','en')==['Hello']
    generate.assert_not_called()

def test_website_story_references_existing_local_pages():
    # Structural check only: fixture-free source catalogue references, no live database.
    from app.db import ROOT
    story=json.loads((ROOT/'sources/timeline.json').read_text(encoding='utf-8'))
    assert len(story['events'])>=8
    for event in story['events']:
        assert event['paragraphs'] and event['sources']
        for source in event['sources']:assert source.get('url','').startswith('https://') or (source['document_id'] and source['page']>=1)
