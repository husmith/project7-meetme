from meetme import Agenda, Appt
import main
import uuid
import datetime
import arrow
import unittest
import nose.tools


class agendaTestClass(unittest.TestCase):

    def setUp(self):
        main.app.config['TESTING'] = True
        self.app = main.app.test_client()
        main.app.secret_key = str(uuid.uuid4())

    def test_status(self):
        """
        Test that app can make initial connection.
        """
        result = self.app.get('/')
        self.assertEqual(result.status_code,200)

    def test_no_free_time(self):
        """
        Tests that Agendas busy during the times a person is free returns no
        possible meeting times.
        """
        begin_time = datetime.time(9,0)
        end_time = datetime.time(17,0)
        begin_date = datetime.date(2015, 9, 2)
        end_date = datetime.date(2015, 9, 10)

        noFreeTimeAgenda = Agenda()
        self.assertEqual(noFreeTimeAgenda.__len__(),0)

        for day in range(2,11):
            noFreeTimeAgenda.append(Appt(datetime.date(2015, 9, day),datetime.time(9, 0), datetime.time(17, 45),"All Hours"))
            noFreeTimeAgenda.append(Appt(datetime.date(2015, 9, day),datetime.time(0, 0), datetime.time(23, 59),"All Hours"))

        self.assertEqual(noFreeTimeAgenda.__len__(),18)

        result = noFreeTimeAgenda.freeblocks(begin_date, end_date, begin_time, end_time)

        self.assertEqual(result.__len__(),0)

    def test_all_free_time(self):
        """
        Tests that an Agenda with events that fall outside of possible meeting Hours
        returns all days in range as possible meeting times.
        """
        begin_time = datetime.time(9,0)
        end_time = datetime.time(17,0)
        begin_date = datetime.date(2015, 12, 1)
        end_date = datetime.date(2015, 12, 4)
        allFreeTimeAgenda = Agenda()
        for day in range(1,5):
            allFreeTimeAgenda.append(Appt(datetime.date(2015, 12, day),datetime.time(6, 30), datetime.time(7, 45),"Before Hours"))
            allFreeTimeAgenda.append(Appt(datetime.date(2015, 12, day),datetime.time(20, 30), datetime.time(21, 45),"After Hours"))

        expected = Agenda()
        for day in range(1,5):
            expected.append(Appt(datetime.date(2015, 12, day),datetime.time(9, 0), datetime.time(17, 0),""))

        result = allFreeTimeAgenda.freeblocks(begin_date, end_date, begin_time, end_time)
        self.assertTrue(result.__eq__(expected),msg="Agendas not equal")

    def test_events_bleed_outside_hours(self):
        """
        Tests that events starting outside of hour range and/or continuing outside
        of hours range are partially factored into the possible meeting times.
        """
        begin_time = datetime.time(9,0)
        end_time = datetime.time(17,0)
        begin_date = datetime.date(2015, 9, 1)
        end_date = datetime.date(2015, 9, 28)

        continueOutsideHoursAgenda = Agenda()

        for day in range(1,29):
            continueOutsideHoursAgenda.append(Appt(datetime.date(2015, 9, day),datetime.time(6, 30), datetime.time(9, 45),"6:30-9:45am"))
            continueOutsideHoursAgenda.append(Appt(datetime.date(2015, 9, day),datetime.time(16, 30), datetime.time(20, 45),"4:30-8:45pm"))

        expected = Agenda()
        for day in range(1,29):
            expected.append(Appt(datetime.date(2015, 9, day),datetime.time(9, 45), datetime.time(16, 30),"6:30-9:45am"))

        result = continueOutsideHoursAgenda.freeblocks(begin_date, end_date, begin_time, end_time)
        self.assertTrue(result.__eq__(expected))


    def test_freeblock_longer_range(self):
        """
        Tests for full day (within hour range) return when less days have events
        than those in the freeblock range.
        """
        begin_time = datetime.time(9,0)
        end_time = datetime.time(17,0)
        begin_date = datetime.date(2015, 9, 1)
        end_date = datetime.date(2015, 9, 18)

        oneWeekAgenda = Agenda()
        for day in range(10,19):
            oneWeekAgenda.append(Appt(datetime.date(2015, 9, day),datetime.time(12, 30), datetime.time(14,20),"12:30-2:20pm"))

        expected = Agenda()
        for day in range(1,10):
            expected.append(Appt(datetime.date(2015, 9, day),datetime.time(9, 0), datetime.time(17,0),"all day"))
        for day in range(10,19):
            expected.append(Appt(datetime.date(2015, 9, day),datetime.time(9, 0), datetime.time(12, 30),"9:00-12:30am"))
            expected.append(Appt(datetime.date(2015, 9, day),datetime.time(14,20), datetime.time(17, 0),"2:20pm-5pm"))

        expected.normalize()
        result = oneWeekAgenda.freeblocks(begin_date, end_date, begin_time, end_time)

        self.assertEqual(result.__len__(),expected.__len__())
        self.assertTrue(result.__eq__(expected))


    def test_arrow_to_appt(self):
        """
        Tests the conversion of arrow objects to Appt.
        """
        test_date_begin = arrow.get('2015-11-20T00:00:00-08:00')
        test_date_end = arrow.get('2015-11-20T15:30:00-08:00')

        self.assertNotEqual(test_date_begin,arrow.arrow.Arrow)

        busy = Appt(test_date_begin.date(),test_date_begin.time(),test_date_end.time(),"Arrow")
        self.assertIsInstance(busy,Appt)
        expected = Appt(datetime.date(2015, 11, 20),datetime.time(0,0),datetime.time(15,30),"Expected")
        self.assertTrue(busy.__eq__(expected))


    def test_different_timezones(self):
        """
        Tests for correct handling of different timezones when converting arrow
        to appointments.
        """
        test_date_pst = arrow.get('2015-11-20T08:00:00-08:00').to('local')
        test_date_gmt = arrow.get('2015-11-20T00:00:00+08:00').to('local')

        self.assertNotEqual(test_date_pst,test_date_gmt)

        appt_pst = Appt(test_date_pst.date(),test_date_pst.time(),datetime.time(12,0),"PST Appt Midnight-4am")
        appt_gmt = Appt(test_date_gmt.date(),test_date_gmt.time(),datetime.time(12,0),"GMT Appt")

        self.assertTrue(appt_pst.__eq__(appt_gmt))

    def test_empty_events(self):
        """
        Tests for all times possible returned when the events are in different month.
        """
        begin_time = datetime.time(9,0)
        end_time = datetime.time(17,0)
        begin_date = datetime.date(2015, 9, 2)
        end_date = datetime.date(2015, 9, 10)

        novemberAgenda = Agenda()

        for day in range(1,11):
            novemberAgenda.append(Appt(datetime.date(2015, 11, day),datetime.time(9, 0), datetime.time(10, 45),"November"))

        result = novemberAgenda.freeblocks(begin_date, end_date, begin_time, end_time)

        self.assertEqual(result.__len__(),9)


    def tearDown(self):
        pass

if __name__ == '__main__':
    unittest.main()
