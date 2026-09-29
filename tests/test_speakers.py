import unittest

from ingestion.pipeline import split_turns


class SpeakerParsingTests(unittest.TestCase):
    def test_unnamed_interjection_is_not_attributed_to_named_member(self):
        turns=split_turns('Shri B. Das: I rise.\nAn Honourable Member : On a point of order, Sir.\nShri B. Das: There is no occasion.')
        self.assertEqual([s for s,t in turns],['Shri B. Das','An Honourable Member','Shri B. Das'])

    def test_office_directory_is_not_a_conversation(self):
        text='President: THE HONOURABLE DR. RAJENDRA PRASAD.\nConstitutional Adviser: SIR B.N. RAU.\nJoint Secretary: MR. MUKHERJEE.\nDeputy Secretary: SHRI KHANNA.\nMarshal: MAJOR JAIDKA.'
        self.assertEqual(split_turns(text),[])

    def test_wrapped_constituency_colon_is_not_a_delimiter(self):
        source='The Honourable Shri Purushottam Das Tandon (United Provinces:\nGeneral) : Sir, I move.\nMr. President: Proceed.'
        self.assertEqual(split_turns(source),[
            ('The Honourable Shri Purushottam Das Tandon','Sir, I move.'),
            ('Mr. President','Proceed.'),
        ])

    def test_wrapped_president_identity_suffix(self):
        self.assertEqual(split_turns('Mr. President (The Honourable\nDr. Rajendra Prasad): Proceed.'),[('Mr. President','Proceed.')])

    def test_constituency_colon_without_speech_delimiter_is_not_a_turn(self):
        source='Shrimati Sucheta Kripalani (U.P.: General) sang the first verse of the song.'
        self.assertEqual(split_turns(source),[])

    def test_corrupt_delimiter_is_not_guessed(self):
        self.assertEqual(split_turns('Shri Biswanath Das (Orissa : General)\ufffd 9 to 1 is not acceptable.'),[])

    def test_constitutional_prose_is_not_a_president_turn(self):
        source='President, shall declare either that he assents to the Bill, or that he withholds assent therefrom:\nProvided that the President may return the Bill.'
        self.assertEqual(split_turns(source),[])

    def test_reported_speech_is_not_a_member_label(self):
        self.assertEqual(split_turns('Dr. B. R. Ambedkar in his memorandum writes:\nA matter of importance.'),[])

    def test_uppercase_printed_label(self):
        self.assertEqual(split_turns('THE HONOURABLE DR. B. R. AMBEDKAR: I move.'),[('THE HONOURABLE DR. B. R. AMBEDKAR','I move.')])

    def test_session_text_is_preserved_without_attributing_it(self):
        self.assertEqual(split_turns('Continuation from the preceding page.\nDr. B. R. Ambedkar: I agree.'),[
            ('Session text','Continuation from the preceding page.'),('Dr. B. R. Ambedkar','I agree.'),
        ])

    def test_hindi_printed_label(self):
        self.assertEqual(split_turns('श्री महावीर त्यागी (संयुक्त प्रान्त: सामान्य): अध्यक्ष महोदय।'),[('श्री महावीर त्यागी','अध्यक्ष महोदय।')])

    def test_inline_references_do_not_split_a_speech(self):
        self.assertEqual(split_turns('Mr. President: As Dr. Ambedkar: has said, we continue.'),[('Mr. President','As Dr. Ambedkar: has said, we continue.')])


if __name__=='__main__':unittest.main()
