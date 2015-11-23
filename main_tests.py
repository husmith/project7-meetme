#########################
#  Self-test invoked when module is run
#  as main program.
#########################
import main
import uuid
import arrow
import unittest
import nose.tools
import flask

class TestApp(unittest.TestCase):

    def setUp(self):
        main.app.config['TESTING'] = True
        self.app = main.app.test_client()
        main.app.secret_key = str(uuid.uuid4())

    def test_status(self):
        result = self.app.get('/')
        self.assertEqual(result.status_code,200)

    def test_two(self):
        with main.app.test_client() as c:
            rv = c.get('/')
            assert flask.session["begin_date"] == ''

    def init_values(self):
        test_date_begin = arrow.get('2015-11-20T00:00:00-08:00')
        test_date_end = test_date_begin.replace(days=+7)
        with main.app.test_client() as c:
            with c.session_transaction() as sess:
                sess["begin_date"] = test_date_begin.floor('day').isoformat()
                sess["end_date"] = test_date_end.ceil('day').isoformat()
        return


    def test_outside_hours(self):
        pass

    def initialize_values(self, begin_date, end_date):
        return self.app.post('/')

    def tearDown(self):
        pass


if __name__ == '__main__':
    unittest.main()








def selftest_appt():
    """Simple smoke test for Appt class."""
    sample = Appt(datetime.date(2012, 10, 31),
                  datetime.time(14, 30), datetime.time(15, 45),
                  "Sample appointment")
    testEQ("Create and format",str(sample),
           "2012.10.31 14:30 15:45 | Sample appointment")

    earlier = Appt(datetime.date(2012, 10, 31),
                    datetime.time(13, 30), datetime.time(14,30),
                    "Before my appt")
    later = Appt(datetime.date(2012, 10, 31),
                  datetime.time(16,00), datetime.time(21,00), "Long dinner")

    testEQ("Strictly before is '<'", earlier < later, True)
    testEQ("Strictly after is '>'", later > earlier, True)
    testEQ("Not earlier than itself", earlier < earlier, False)
    testEQ("Not later than itself", earlier > later, False)

    testEQ("Earlier doesn't overlap later", earlier.overlaps(later), False)
    testEQ("Later doesn't overlap earlier", later.overlaps(earlier), False)

    conflict = Appt(datetime.date(2012, 10, 31),
                    datetime.time(13, 45), datetime.time(16,00),
        "Conflicting appt")

    testEQ("Should overlap", sample.overlaps(conflict), True)
    testEQ("Opposite overlap", conflict.overlaps(sample), True)
    overlap = sample.intersect(conflict)
    testEQ("Expected intersection", str(overlap),
           "2012.10.31 14:30 15:45 | Sample appointment")
    overlap = conflict.intersect(sample)
    testEQ("Expected intersection", str(overlap),
           "2012.10.31 14:30 15:45 | Conflicting appt")
    overlap = conflict.intersect(sample,"New desc")
    testEQ("Expected intersection", str(overlap),
           "2012.10.31 14:30 15:45 | New desc")

    text = "2012.10.31 14:30 15:45 | from text"
    from_text = Appt.from_string(text)
    testEQ("String <-> Appt",text, str(from_text))
    def die():
       Appt.from_string("2012.10.31 15:45 14:30 | time traveler")
    testRaise("Time order error", ValueError, die)


def selftest_agenda():
    """Simple smoke test for Agenda class."""

    keiko_agtxt="""# Free times for Keiko on December 1
           2012.12.1 07:00 08:00  | Possible breakfast meeting
           2012.12.1 10:00 12:00  | Late morning meeting
           2012.12.1 14:00 18:00  | Afternoon meeting
         """

    kevin_agtxt="""2012.11.30 09:00 14:00 | I have an afternoon commitment on the 30th
          2012.12.1  09:00 15:00 | I prefer morning meetings
          # Kevin always prefers morning, but can be available till 3, except for
          # 30th of November.
          """

    emanuela_agtxt = """
    2012.12.1 12:00 14:00 | Early afternoon
    2012.12.1 16:00 18:00 | Late afternoon into evening
    2012.12.2 8:00 17:00 | All the next day
    """

    keiko_ag = Agenda.from_file(io.StringIO(keiko_agtxt))
    kevin_ag = Agenda.from_file(io.StringIO(kevin_agtxt))
    emanuela_ag = Agenda.from_file(io.StringIO(emanuela_agtxt))

    keiko_kevin = keiko_ag.intersect(kevin_ag)
    kk = ("2012.12.01 10:00 12:00 | Late morning meeting\n" +
         "2012.12.01 14:00 15:00 | Afternoon meeting")
    kkactual = str(keiko_kevin)
    testEQ("Keiko and Kevin", kkactual.strip(), kk.strip())

    kevin_emanuela = kevin_ag.intersect(emanuela_ag)
    ke = "2012.12.01 12:00 14:00 | I prefer morning meetings"
    keactual = str(kevin_emanuela)
    testEQ("Kevin and Emanuela", keactual, ke)

    everyone = keiko_kevin.intersect(emanuela_ag)
    testEQ("No overlap of all three", len(everyone), 0)

def selftest2_agenda():

    print("""
    **********************************
    *** Smoke test Agenda addenda   **
    *** normalization and complement**
    ********************************""")

    """Additional tests for agenda normalization and complement."""
    # What could go wrong in sorting?
    keiko_agtxt="""2013.12.2 12:00 14:00 | Late lunch
                   2013.12.1 13:00 14:00 | Sunday brunch
                   2013.12.2 08:00 15:00 | Long long meeting
                   2013.12.2 15:00 16:00 | Coffee after the meeting"""
    keiko_ag = Agenda.from_file(io.StringIO(keiko_agtxt))

    # Torture test for normalization
    day_in_life_agtxt = """
# A torture-test agenda.  I am seeing a lot of code
# that may not work well with sequences of three or more
# appointments that need to be merged.  Here's an agenda
# with such a sequence.  Also some Beatles lyrics that have
# been running through my head.
#
2013.11.26 09:00 10:30 | got up
2013.11.26 10:00 11:30 | got out of bed
2013.11.26 11:00 12:30 | drug a comb across my head
2013.11.26 12:00 13:30 | on the way down stairs I had a smoke
2013.11.26 13:00 14:30 | and somebody spoke
2013.11.26 14:00 15:30 | and I went into a dream
#
# A gap here, from 15:30 to 17:00
#
2013.11.26 17:00  18:30 | he blew his mind out in a car
2013.11.26 18:00  19:30 | hadn't noticed that the lights had changed
2013.11.26 19:00  20:30 | a crowd of people stood and stared
#
# A gap here, from 20:30 to 21:00
#
2013.11.26 21:00 22:30 | they'd seen his face before
2013.11.26 22:00 23:00 | nobody was really sure ..."""
    day_in_life = Agenda.from_file(io.StringIO(day_in_life_agtxt))
    day_in_life.normalize()
    # How are we going to test this?  I want to ignore the text descriptions.
    # Defined __eq__ method in Agenda just for this
    should_be_txt = """
    2013.11.26 09:00 15:30 | I read the news today oh, boy
    2013.11.26 17:00 20:30 | about a lucky man who made the grade
    2013.11.26 21:00 23:00 | and though the news was rather sad
    """
    should_be_ag = Agenda.from_file(io.StringIO(should_be_txt))
    testEQ("Torture test normalized",day_in_life,should_be_ag)

    # Start with the simplest cases of "complement"
    simple_agtxt = """2013.12.01 12:00 14:00 | long lunch"""
    simple_ag = Agenda.from_file(io.StringIO(simple_agtxt))

    # Different day - should have no effect
    tomorrow = Appt.from_string("""2013.12.02 11:00 15:00 | tomorrow""")
    simple_ag = simple_ag.complement(tomorrow)
    testEQ("Yesterday's appts don't matter",str(simple_ag).strip(),
           """2013.12.02 11:00 15:00 | tomorrow""")
    # And the freeblock should not be altered
    testEQ("Not clobber freeblock",str(tomorrow),
           """2013.12.02 11:00 15:00 | tomorrow""")

    # Freeblock completely covered
    simple_agtxt = """2013.12.01 12:00 14:00 | long lunch"""
    simple_ag = Agenda.from_file(io.StringIO(simple_agtxt))
    lunch = Appt.from_string("""2013.12.01 12:30 13:30 | lunch""")
    simple_ag = simple_ag.complement(lunch)
    testEQ("Completely blocked freeblock",str(simple_ag).strip(),"")
    # And the freeblock should not be altered
    testEQ("Not clobber freeblock 2",str(lunch),
           """2013.12.01 12:30 13:30 | lunch""")

    # Freeblock different times same day
    simple_agtxt = """2013.12.01 12:00 14:00 | long lunch"""
    simple_ag = Agenda.from_file(io.StringIO(simple_agtxt))
    dinner = Appt.from_string("""2013.12.01 19:30 20:30 | dinner""")
    simple_ag = simple_ag.complement(dinner)
    testEQ("Freeblock later in day",str(simple_ag).strip(),
           """2013.12.01 19:30 20:30 | dinner""")
    #
    # More complex agendas - try with two appointments
    #
    simple_agtxt = """
    2013.12.01 9:00 11:00 | morning meeting
    2013.12.01 13:00 14:00 | afternoon meeting"""
    # Cover first part first appt
    simple_ag = Agenda.from_file(io.StringIO(simple_agtxt))
    part_cover_first = Appt.from_string("2013.12.01 08:30 09:30 | morning coffee")
    simple_ag = simple_ag.complement(part_cover_first)
    testEQ("Freeblock partly covers first appt start only",
           str(simple_ag).strip(), "2013.12.01 08:30 09:00 | morning coffee")
    # Cover last part first appt
    simple_ag = Agenda.from_file(io.StringIO(simple_agtxt))
    part_cover_first = Appt.from_string("2013.12.01 09:30 11:30 | morning coffee")
    simple_ag = simple_ag.complement(part_cover_first)
    testEQ("Freeblock partly covers first appt end only",
           str(simple_ag).strip(), "2013.12.01 11:00 11:30 | morning coffee")
    # Cover first part second appt
    simple_ag = Agenda.from_file(io.StringIO(simple_agtxt))
    part_cover_first = Appt.from_string("2013.12.01 12:30 13:30 | afternoon coffee")
    simple_ag = simple_ag.complement(part_cover_first)
    testEQ("Freeblock partly covers second appt start only",
           str(simple_ag).strip(), "2013.12.01 12:30 13:00 | afternoon coffee")
    # Cover last part second appt
    simple_ag = Agenda.from_file(io.StringIO(simple_agtxt))
    part_cover_first = Appt.from_string("2013.12.01 13:30 14:30 | afternoon coffee")
    simple_ag = simple_ag.complement(part_cover_first)
    testEQ("Freeblock partly covers second appt end only",
           str(simple_ag).strip(), "2013.12.01 14:00 14:30 | afternoon coffee")
    # Cover middle part two appts
    simple_ag = Agenda.from_file(io.StringIO(simple_agtxt))
    part_cover_first = Appt.from_string("2013.12.01 10:30 13:30 | mid-day")
    simple_ag = simple_ag.complement(part_cover_first)
    testEQ("Freeblock partly covers two appts and gap",
           str(simple_ag).strip(), "2013.12.01 11:00 13:00 | mid-day")
    # Extend across two appts
    simple_ag = Agenda.from_file(io.StringIO(simple_agtxt))
    part_cover_first = Appt.from_string("2013.12.01 08:00 15:00 | most of day")
    simple_ag = simple_ag.complement(part_cover_first)
    testEQ("Freeblock fully covers two appts and gap",
           str(simple_ag).strip(), "2013.12.01 08:00 09:00 | most of day" +
           "\n" + "2013.12.01 11:00 13:00 | most of day" +
           "\n" + "2013.12.01 14:00 15:00 | most of day")

if __name__ == "__main__":
    selftest_appt()
    selftest_agenda()
    selftest2_agenda()
