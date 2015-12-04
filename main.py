import flask
from flask import render_template
from flask import request
from flask import url_for
from flask import jsonify
from collections import defaultdict
import uuid

import string
import random
import json
import logging

from meetme import Agenda, Appt

# Date handling
import arrow # Replacement for datetime, based on moment.js
from datetime import datetime, date, time, timedelta, tzinfo # But we still need time
from dateutil import tz  # For interpreting local times


# OAuth2  - Google library implementation for convenience
from oauth2client import client
import httplib2   # used in oauth2 flow

# Google API for services
from apiclient import discovery

# Mongo database
from pymongo import MongoClient
from bson.objectid import ObjectId
from flask import jsonify
###
# Globals
###
import CONFIG
app = flask.Flask(__name__)

try:
    dbclient = MongoClient(CONFIG.MONGO_URL)
    db = dbclient.meetme
    collection = db.meetings

except:
    print("Failure opening database.  Is Mongo running? Correct password?")
    sys.exit(1)

import uuid
app.secret_key = str(uuid.uuid4())


SCOPES = 'https://www.googleapis.com/auth/calendar.readonly'
CLIENT_SECRET_FILE = CONFIG.GOOGLE_LICENSE_KEY  ## You'll need this
APPLICATION_NAME = 'googly'

#############################
#
#  Pages (routed from URLs)
#
#############################

@app.route("/")
@app.route("/index")
def index():
  app.logger.debug("Entering index")

  if 'use_gcal' in flask.session and flask.session['use_gcal']:
    credentials = valid_credentials()
    if not credentials:
      return flask.redirect(flask.url_for('oauth2callback'))
  if 'begin_date' not in flask.session:
      init_session_values()
  if 'available_other' in flask.session:
      available_o = get_meetings(flask.session['available_other'])
      return render_template('index.html',other_meetings=available_o)
  return render_template('index.html')

#key: CKN23
@app.route("/busy/<key>")
@app.route("/meetings/<key>")
def meeting_data(key):
    #check if user is same
    flask.session['available_other'] = key
    if 'use_gcal' in flask.session and flask.session['use_gcal']:
      credentials = valid_credentials()
      if not credentials:
        return flask.redirect(flask.url_for('oauth2callback'))
    if 'begin_date' not in flask.session:
        init_given_values(key)
    return flask.render_template('busy.html',other_meetings=get_meetings(key))

@app.route("/getmycals")
def othercals():
    ## We'll need authorization to list calendars
    ## I wanted to put what follows into a function, but had
    ## to pull it back here because the redirect has to be a
    ## 'return'
    app.logger.debug("Checking credentials for Google calendar access")
    credentials = valid_credentials()
    if not credentials:
      app.logger.debug("Redirecting to authorization")
      return flask.redirect(flask.url_for('oauth2callback'))
    gcal_service = get_gcal_service(credentials)
    app.logger.debug("Returned from get_gcal_service")
    flask.session['calendars'] = list_calendars(gcal_service)
    return flask.redirect(url_for('busy', key=flask.session['available_other']))


@app.route("/getcals")
def choose():
    ## We'll need authorization to list calendars
    ## I wanted to put what follows into a function, but had
    ## to pull it back here because the redirect has to be a
    ## 'return'
    app.logger.debug("Checking credentials for Google calendar access")
    credentials = valid_credentials()
    if not credentials:
      app.logger.debug("Redirecting to authorization")
      return flask.redirect(flask.url_for('oauth2callback'))
    gcal_service = get_gcal_service(credentials)
    app.logger.debug("Returned from get_gcal_service")
    flask.session['calendars'] = list_calendars(gcal_service)
    return flask.redirect('index')

####
#
#  Google calendar authorization:
#      Returns us to the main /choose screen after inserting
#      the calendar_service object in the session state.  May
#      redirect to OAuth server first, and may take multiple
#      trips through the oauth2 callback function.
#
#  Protocol for use ON EACH REQUEST:
#     First, check for valid credentials
#     If we don't have valid credentials
#         Get credentials (jump to the oauth2 protocol)
#         (redirects back to /choose, this time with credentials)
#     If we do have valid credentials
#         Get the service object
#
#  The final result of successful authorization is a 'service'
#  object.  We use a 'service' object to actually retrieve data
#  from the Google services. Service objects are NOT serializable ---
#  we can't stash one in a cookie.  Instead, on each request we
#  get a fresh serivce object from our credentials, which are
#  serializable.
#
#  Note that after authorization we always redirect to /choose;
#  If this is unsatisfactory, we'll need a session variable to use
#  as a 'continuation' or 'return address' to use instead.
#
####

def valid_credentials():
    """
    Returns OAuth2 credentials if we have valid
    credentials in the session.  This is a 'truthy' value.
    Return None if we don't have credentials, or if they
    have expired or are otherwise invalid.  This is a 'falsy' value.
    """
    if 'credentials' not in flask.session:
      return None

    credentials = client.OAuth2Credentials.from_json(
        flask.session['credentials'])

    if (credentials.invalid or
        credentials.access_token_expired):
      return None
    return credentials


def get_gcal_service(credentials):
  """
  We need a Google calendar 'service' object to obtain
  list of calendars, busy times, etc.  This requires
  authorization. If authorization is already in effect,
  we'll just return with the authorization. Otherwise,
  control flow will be interrupted by authorization, and we'll
  end up redirected back to /choose *without a service object*.
  Then the second call will succeed without additional authorization.
  """
  app.logger.debug("Entering get_gcal_service")
  http_auth = credentials.authorize(httplib2.Http())
  service = discovery.build('calendar', 'v3', http=http_auth)
  app.logger.debug("Returning service")
  return service

@app.route('/oauth2callback')
def oauth2callback():
  """
  The 'flow' has this one place to call back to.  We'll enter here
  more than once as steps in the flow are completed, and need to keep
  track of how far we've gotten. The first time we'll do the first
  step, the second time we'll skip the first step and do the second,
  and so on.
  """
  app.logger.debug("Entering oauth2callback")
  flow =  client.flow_from_clientsecrets(
      CLIENT_SECRET_FILE,
      scope= SCOPES,
      redirect_uri=flask.url_for('oauth2callback', _external=True))
## Note we are *not* redirecting above.  We are noting *where*
  ## we will redirect to, which is this function.

  ## The *second* time we enter here, it's a callback
  ## with 'code' set in the URL parameter.  If we don't
  ## see that, it must be the first time through, so we
  ## need to do step 1.
  app.logger.debug("Got flow")
  if 'code' not in flask.request.args:
    app.logger.debug("Code not in flask.request.args")
    auth_uri = flow.step1_get_authorize_url()
    return flask.redirect(auth_uri)
    ## This will redirect back here, but the second time through
    ## we'll have the 'code' parameter set
  else:
    ## It's the second time through ... we can tell because
    ## we got the 'code' argument in the URL.
    app.logger.debug("Code was in flask.request.args")
    auth_code = flask.request.args.get('code')
    credentials = flow.step2_exchange(auth_code)
    flask.session['credentials'] = credentials.to_json()
    ## Now I can build the service and execute the query,
    ## but for the moment I'll just log it and go back to
    ## the main screen
    app.logger.debug("Got credentials")
    flask.flash('Setting option to use Google calendars')
    flask.session['use_gcal'] = True
    if 'available_other' in flask.session:
        return flask.redirect('busy')
    return flask.redirect('index')

#####
#
#  Option setting:  Buttons or forms that add some
#     information into session state.  Don't do the
#     computation here; use of the information might
#     depend on what other information we have.
#   Setting an option sends us back to the main display
#      page, where we may put the new information to use.
#
#####

@app.route('/setrange', methods=['POST'])
def setrange():
    """
    User chose a date range with the bootstrap daterange
    widget.
    """
    app.logger.debug("Entering setrange")
    flask.flash("Setrange gave us '{}'".format(
      request.form.get('daterange')))
    daterange = request.form.get('daterange')
    flask.session['daterange'] = daterange
    daterange_parts = daterange.split(' - ')
    flask.session['begin_date'] = interpret_date(daterange_parts[0])
    flask.session['end_date'] = interpret_date(daterange_parts[1])
    # flask.session['begin_time'] = request.form.get('begin-time')
    # flask.session['end_time'] = request.form.get('end-time')
    app.logger.debug("Setrange parsed {} - {}  dates as {} - {}".format(
      daterange_parts[0], daterange_parts[1],
      flask.session['begin_date'], flask.session['end_date']))
    return flask.redirect('index')

####
#
#   Initialize session variables
#
####

def init_session_values():
    """
    Start with some reasonable defaults for date and time ranges.
    Note this must be run in app context ... can't call from main.
    """
    # Default date span = tomorrow to 1 week from now
    now = arrow.now('local')
    tomorrow = now.replace(days=+1)
    nextweek = now.replace(days=+7)
    flask.session["begin_date"] = tomorrow.floor('day').isoformat()
    flask.session["end_date"] = nextweek.ceil('day').isoformat()
    flask.session["daterange"] = "{} - {}".format(
        tomorrow.format("MM/DD/YYYY"),
        nextweek.format("MM/DD/YYYY"))
    # Default time span each day, 8 to 5
    flask.session["begin_time"] = interpret_time("9am")
    flask.session["end_time"] = interpret_time("5pm")

def init_given_values(key):
    """
    Start with some reasonable defaults for date and time ranges.
    Note this must be run in app context ... can't call from main.
    """
    # Default date span = tomorrow to 1 week from now
    now = arrow.now('local')
    tomorrow = now.replace(days=+1)
    nextweek = now.replace(days=+7)
    flask.session["begin_date"] = tomorrow.floor('day').isoformat()
    flask.session["end_date"] = nextweek.ceil('day').isoformat()
    flask.session["daterange"] = "{} - {}".format(
        tomorrow.format("MM/DD/YYYY"),
        nextweek.format("MM/DD/YYYY"))
    flask.session["begin_time"] = interpret_time("9am")
    flask.session["end_time"] = interpret_time("5pm")


def interpret_time( text ):
    """
    Read time in a human-compatible format and
    interpret as ISO format with local timezone.
    May throw exception if time can't be interpreted. In that
    case it will also flash a message explaining accepted formats.
    """
    app.logger.debug("Decoding time '{}'".format(text))
    time_formats = ["ha", "h:mma",  "h:mm a", "H:mm"]
    try:
        as_arrow = arrow.get(text, time_formats).replace(tzinfo=tz.tzlocal())
        app.logger.debug("Succeeded interpreting time")
    except:
        app.logger.debug("Failed to interpret time")
        flask.flash("Time '{}' didn't match accepted formats 13:30 or 1:30pm"
              .format(text))
        raise
    return as_arrow.isoformat()

def interpret_date( text ):
    """
    Convert text of date to ISO format used internally,
    with the local time zone.
    """
    try:
      as_arrow = arrow.get(text, "MM/DD/YYYY").replace(
          tzinfo=tz.tzlocal())
    except:
        flask.flash("Date '{}' didn't fit expected format 12/31/2001")
        raise
    return as_arrow.isoformat()

def next_day(isotext):
    """
    ISO date + 1 day (used in query to Google calendar)
    """
    as_arrow = arrow.get(isotext)
    return as_arrow.replace(days=+1).isoformat()

####
#
#  Functions (NOT pages) that return some information
#
####
def generate_key():
    ran = ''.join([random.choice(string.ascii_letters + string.digits) for n in range(5)])
    return ran

def put_meetings(meetings,key):
    """
    Place memo into database
    Args:
       dt: Datetime (arrow) object
       mem: Text of memo
    NOT TESTED YET
    """
    key_dict = {"key":key}
    available = []
    for appt in meetings.appts:
        meet = {"start": appt.begin, "end": appt.end}
        meet.update(key_dict)
        collection.insert(meet)
        available.append(meet)

    print(str(available))

    return


def get_meetings(key):
    records = []
    meetings = collection.find({"key":key}).sort('start',1)
    other_agenda = Agenda()
    for meeting in meetings:
        time = Appt(meeting['start'].date(),meeting['start'].time(),meeting['end'].time(),"meetme")
        other_agenda.append(time);

    print(str(other_agenda))
    return other_agenda

def list_calendars(service):
    """
    Given a google 'service' object, return a list of
    calendars.  Each calendar is represented by a dict, so that
    it can be stored in the session object and converted to
    json for cookies. The returned list is sorted to have
    the primary calendar first, and selected (that is, displayed in
    Google Calendars web app) calendars before unselected calendars.
    """
    app.logger.debug("Entering list_calendars")
    calendar_list = service.calendarList().list().execute()["items"]
    result = [ ]
    for cal in calendar_list:
        kind = cal["kind"]
        id = cal["id"]
        if "description" in cal:
            desc = cal["description"]
        else:
            desc = "(no description)"
        summary = cal["summary"]
        # Optional binary attributes with False as default
        selected = ("selected" in cal) and cal["selected"]
        primary = ("primary" in cal) and cal["primary"]


        result.append(
          { "kind": kind,
            "id": id,
            "summary": summary,
            "selected": selected,
            "primary": primary
            })
    return sorted(result, key=cal_sort_key)


@app.route("/intersection")
def intersection():
    to_intersect = request.form.getlist('time')
    credentials = valid_credentials()
    service = get_gcal_service(credentials)

    # Agenda of all the events that occur within the specified date range
    busy_times = Agenda()
    other_times = Agenda()
    for ot in to_intersect:
        other_times.append(ot)
    app.logger.debug(other_times)
    # begin_time = to_intersec
    # print(str(begin_time))
    # end_time = meetings.find().sort({'end':-1}).limit(1)
    # print(str(begin_time))
    # For each calendar, get the events within the specified range
    min_date = min(other_times.appts,key=lambda x:x.begin)
    max_date = max(other_times.appts,key=lambda x: x.end)

    for cal in calids:
        app.logger.debug("Getting free times between "+min_date+" and "+max_date)
        events = service.events().list(calendarId=cal,singleEvents=True,timeMin=min_date,timeMax=max_date).execute()

        for event in events['items']:
            busy = Appt(arrow.get(event['start']['dateTime']).date(),arrow.get(event['start']['dateTime']).time(),arrow.get(event['end']['dateTime']).time(),"busy")
            busy_times.append(busy)


    begin_date = arrow.get(begin_time.date())
    end_date = arrow.get(end_time.date())

    begin_time = arrow.get(flask.session['begin_time']).time()
    end_time = arrow.get(flask.session['end_time']).time()

    # Calling normalize makes sure that overlapping events are merged
    busy_times.normalize()

    # Make a new Agenda with all the free times
    meetings = busy_times.freeblocks(begin_date, end_date, begin_time, end_time)
    # Merge overlapping free times (if they exist) as a precaution
    meetings.normalize()
    # put_meetings(meetings,key=generate_key());



@app.route("/blocktimes", methods=['POST','GET'])
def blocktimes():
    """
    Retrieves the events from the selected calendars using the Google Calendar API.
    Events are inserted into an Agenda as Appointements. Agenda.freeblock then returns
    an Agenda of the possible meeting times, which is then rendered on the webpage.
    """
    app.logger.debug("Entering blocktimes")

    # Get ids of selected calendars from form
    calids = request.form.getlist('calid')

    credentials = valid_credentials()
    service = get_gcal_service(credentials)
    app.logger.debug("Returned from get_gcal_service")

    # Agenda of all the events that occur within the specified date range
    busy_times = Agenda()

    # For each calendar, get the events within the specified range
    for cal in calids:
        app.logger.debug("Getting free times between "+flask.session['begin_date']+" and "+flask.session['end_date'])
        events = service.events().list(calendarId=cal,singleEvents=True,timeMin=flask.session['begin_date'],timeMax=flask.session['end_date']).execute()

        for event in events['items']:
            busy = Appt(arrow.get(event['start']['dateTime']).date(),arrow.get(event['start']['dateTime']).time(),arrow.get(event['end']['dateTime']).time(),"busy")
            busy_times.append(busy)

    begin_date = arrow.get(flask.session['begin_date'])
    end_date = arrow.get(flask.session['end_date'])

    begin_time = arrow.get(flask.session['begin_time']).time()
    end_time = arrow.get(flask.session['end_time']).time()


    # Calling normalize makes sure that overlapping events are merged
    busy_times.normalize()

    # Make a new Agenda with all the free times
    meetings = busy_times.freeblocks(begin_date, end_date, begin_time, end_time)
    # Merge overlapping free times (if they exist) as a precaution
    meetings.normalize()
    # put_meetings(meetings,key=generate_key());

    if 'available_other' in flask.session:
        available_o = get_meetings(flask.session['available_other'])
        available_intersect = meetings.intersect(available_o)
        available_intersect.normalize()
        app.logger.debug("meetings:")
        print(str(meetings))
        app.logger.debug("other:")
        print(str(available_o))
        app.logger.debug("Returning intersect")
        return flask.render_template('index.html',meetings=available_intersect,oother_meetings=available_o)

    return flask.render_template('index.html',meetings=meetings)


def cal_sort_key( cal ):
    """
    Sort key for the list of calendars:  primary calendar first,
    then other selected calendars, then unselected calendars.
    (" " sorts before "X", and tuples are compared piecewise)
    """
    if cal["selected"]:
       selected_key = " "
    else:
       selected_key = "X"
    if cal["primary"]:
       primary_key = " "
    else:
       primary_key = "X"
    return (primary_key, selected_key, cal["summary"])


#################
#
# Functions used within the templates
#
#################

@app.template_filter( 'fmtdate' )
def format_arrow_date( date ):
    try:
        normal = arrow.get( date )
        return normal.format("ddd MM/DD/YYYY")
    except:
        return "(bad date)"

@app.template_filter( 'fmttime' )
def format_arrow_time( time ):
    try:
        normal = arrow.get( time )
        return normal.format("HH:mm")
    except:
        return "(bad time)"

#############


if __name__ == "__main__":
  # App is created above so that it will
  # exist whether this is 'main' or not
  # (e.g., if we are running in a CGI script)

  app.secret_key = str(uuid.uuid4())
  app.debug=CONFIG.DEBUG
  app.logger.setLevel(logging.DEBUG)
  # We run on localhost only if debugging,
  # otherwise accessible to world
  # if CONFIG.DEBUG:
    # Reachable only from the same computer
    # app.run(port=CONFIG.PORT)
  # else:
    # Reachable from anywhere
  app.run(port=CONFIG.PORT,host="0.0.0.0")
