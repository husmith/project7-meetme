#! /usr/bin/env python3

""" For deployment on ix under CGI """
print("Content-Type: text/html")
import site
site.addsitedir("/home/faculty/michal/public_html/htbin/cis322/proj2-flask/env/lib/python3.4/site-packages")

from wsgiref.handlers import CGIHandler
from main import app

CGIHandler().run(app)
