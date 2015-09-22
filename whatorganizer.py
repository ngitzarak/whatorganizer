import sys
import os
import re
import libtorrent
import whatapi
from optparse import OptionParser
import hashlib
import urllib
import pickle
from pprint import pprint
from getpass import getpass
from time import sleep
import sqlite3
import datetime
import pymongo

parser = OptionParser(usage="Usage: %prog [options] filedir", version="%prog 0.1")
parser.add_option("-w", "--torrentdir", help="Directory with .torrent files", dest="torrentdir")
parser.add_option("-y", "--symdir", help="Directory to maintain symlinks", dest="symdir")
parser.add_option("-u", "--username", help="What.CD username (mandatory on first login)", dest="username")
parser.add_option("-p", "--password", help="What.CD password (optional, can be entered interactively)", dest="password")
parser.add_option("--amount", help="Only do specific amount of lookups", dest="amount", type="int", default=-1)


(options,args) = parser.parse_args()

try:
	client = pymongo.MongoClient()
except pymongo.errors.ConnectionFailure, e:
	print "Could not connect to MongoDB: %s" % e
db = client.whatorganizer
torrents = db.torrents

try:
	cookies = pickle.load(open(".cookies", "rb"))
except:
	cookies = ""
	
if not options.username or not options.torrentdir or not options.symdir or len(args) != 1:
	parser.print_help()
	exit(-1)

musicdir=args[0]

#if new_db:
#	db['cookies'] = []
if not cookies and not options.password:
	options.password = getpass("Password: ")

try:
	apihandle = whatapi.WhatAPI(username=options.username, password=options.password, cookies=cookies)
except whatapi.whatapi.LoginException:
	print "Login failed"
	exit(-1)

pickle.dump(apihandle.session.cookies, open('.cookies', 'wb'))


def create_symlink(torrent):
	for tag in torrent['torrent_info']['group']['tags']:
		tagdir = os.path.join(options.symdir, tag)
		try:
			os.stat(tagdir)
		except:
			os.mkdir(tagdir)
		if not os.path.islink(os.path.join(tagdir, torrent['name'])):
			os.symlink(os.path.join(musicdir,torrent['name']), os.path.join(tagdir,torrent['name']))
			print "Created symlink: " + os.path.join(tagdir,torrent['name']) + " -> " + os.path.join(musicdir,torrent['name'])
	
n = options.amount
for subdir, dirs, files in os.walk(options.torrentdir):
	for file in files:
		if re.match(".+\\.torrent$", file):
			info = libtorrent.torrent_info(os.path.join(subdir, file))
			info_hash = str.upper(str(info.info_hash()))
			name = info.name()
			for t in info.trackers():
				if re.match("http://tracker\\.what\\.cd.+", t.url):
					whatcd_torrent = True
				else:
					whatcd_torrent = False
				
			
			
			#torrentdata = open(os.path.join(subdir,file)).read()
			#torrent = decode(torrentdata)
			
			#print urllib.urlencode(hashlib.sha1(torrent["info"]))
			
			if not whatcd_torrent:
				continue
			
			
			if torrents.find_one({'info_hash': info_hash}):
				#print "Torrent already in db"
				continue
			
			if n == 0:
				print "Looked up "+str(options.amount)+" torrents"
				break
			n -= 1
			
			t_a = datetime.datetime.now()
			
			result = apihandle.request('torrent', hash=info_hash)
			if result['status'] == "success":
				torrents.insert_one({'info_hash': info_hash, 'name': name, 'torrent_info': result['response']})
				create_symlink(torrents.find_one({'info_hash': info_hash}))
				print name + " added"
			else:
				print "Error: "+result
			
			
			t_b = datetime.datetime.now()
			t_c = t_b-t_a
			
			print str(t_c.seconds + t_c.microseconds/1000000.) + " seconds"
			
			if (t_c.seconds*1000000 + t_c.microseconds) > 2000000:
				sleep((1./2000)-(1./(t_c.seconds*1000 + t_c.microseconds/1000.)))
			


#for torrent in db.torrents.find():
#	create_symlink(torrent)
