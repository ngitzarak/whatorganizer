#!/usr/bin/env python

import sys
import os
import re
import libtorrent
import whatapi
from optparse import OptionParser
import hashlib
import urllib
import pickle
from getpass import getpass
from time import sleep
import sqlite3
import datetime
import pymongo
import shutil

parser = OptionParser(usage="Usage: %prog [options] filedir", version="%prog 0.1")
parser.add_option("-w", "--torrentdir", help="Directory with .torrent files", dest="torrentdir")
parser.add_option("-l", "--libdir", help="Directory to maintain library", dest="libdir")
parser.add_option("-u", "--username", help="What.CD username (mandatory on first login)", dest="username")
parser.add_option("-p", "--password", help="What.CD password (optional, can be entered interactively)", dest="password")
parser.add_option("-x", "--freq", help="Minimum interval between lookups in seconds (minimum 2)", dest="interval", type="float", default=2.)
parser.add_option("--rebuild", help="Rebuild the library dir", dest="rebuild", action="store_true", default=False)
parser.add_option("--rebuild-favourites", help="Rebuild favourites", dest="rebuild_favourites", action="store_true", default=False)


try:
	client = pymongo.MongoClient()
except pymongo.errors.ConnectionFailure, e:
	print "Could not connect to MongoDB: %s" % e
db = client.whatorganizer
torrents = db.torrents



(options,args) = parser.parse_args()

musicdir=args[0]

favourites = [(d, sorted(d.split())) for d in os.listdir(os.path.join(options.libdir, "Favourites")) if os.path.isdir(os.path.join(options.libdir, "Favourites", d))]
#for subdir, dirs, files in os.walk(os.path.join(options.libdir, "Favourites")):
#	for dir in dirs:
#		favourites.append((dir,sorted(dir.split())))

def what_favourites(torrent):
	is_in = []
	for f in favourites:
		n_m = 0
		for i in f[1]:
			if i in torrent['torrent_info']['group']['tags']:
				n_m += 1
		if n_m == len(f[1]):
			is_in.append(f)
	return is_in



def create_symlinks(torrent):
	for tag in torrent['torrent_info']['group']['tags']:
		if not tag:
			tag = "_NO_TAGS_"
		tagdir = os.path.join(options.libdir, "Tags", tag)
		try:
			os.stat(tagdir)
		except:
			os.mkdir(tagdir)
		if not os.path.islink(os.path.join(tagdir, torrent['name'])):
			#if options.tagsinlink:
			#	tagdesc = "[ "
			#	for _tag in torrent['torrent_info']['group']['tags']:
			#		if _tag:
			#			tagdesc += _tag + " "
			#	tagdesc += "]"
			#	os.symlink(os.path.join(musicdir,torrent['name']), os.path.join(tagdir,torrent['name']+" "+tagdesc))
			#else:

			if os.path.isdir(os.path.join(musicdir, torrent['name'])):
				os.symlink(os.path.join(musicdir,torrent['name']), os.path.join(tagdir,torrent['name']))
			#print "Created symlink: " + os.path.join(tag,torrent['name']) + " -> " + os.path.join(musicdir,torrent['name'])
	g_info =  torrent['torrent_info']['group']
	try:
		if not g_info['musicInfo']:
			return
		
		for artist in torrent['torrent_info']['group']['musicInfo']['artists']:
			a_dir = os.path.join(options.libdir, "Artists", artist['name'].replace("/",'+'))
			try:
				os.stat(a_dir)
			except:
				os.mkdir(a_dir)
			if not os.path.islink(os.path.join(a_dir, torrent['name'])):
				os.symlink(os.path.join(musicdir, torrent['name']), os.path.join(a_dir, torrent['name']))
	except Exception,e:
		print e
		print g_info
		exit(-1)
	
	w = what_favourites(t)
	if w:
		for i in w:
			f_dir = os.path.join(options.libdir, 'Favourites', i[0])
			if not os.path.islink(os.path.join(f_dir, torrent['name'])):
				os.symlink(os.path.join(musicdir, torrent['name']), os.path.join(f_dir, torrent['name']))
def init_folders():
	try:
		os.stat(options.libdir)
	except:
		os.mkdir(options.libdir)
	try:
		os.stat(os.path.join(options.libdir, "Tags"))
	except:
		os.mkdir(os.path.join(options.libdir, "Tags"))
	try:
		os.stat(os.path.join(options.libdir, "Artists"))
	except:
		os.mkdir(os.path.join(options.libdir, "Artists"))
	try:
		os.stat(os.path.join(options.libdir, "Favourites"))
	except:
		os.mkdir(os.path.join(options.libdir, "Favourites"))		



def create_tagsmeta():
	meta = open(os.path.join(options.libdir,"tagsmeta"), "w")
	for t in torrents.find(): #.sort([('name', 1)]):
		meta.write(t["name"].encode('utf8'))
		meta.write(" [ ")
		for i in t['torrent_info']['group']['tags']:
			meta.write(i + " ")
		meta.write("]\n")
	meta.close()


		
		

try:
	cookies = pickle.load(open(".cookies", "rb"))
except:
	cookies = ""

if not options.username or not options.torrentdir or not options.libdir or options.interval < 2. or len(args) != 1:
	parser.print_help()
	exit(-1)



if options.rebuild_favourites:
	init_folders()
	
	for f in favourites:
		shutil.rmtree(os.path.join(options.libdir, 'Favourites', f[0]))
		os.mkdir(os.path.join(options.libdir, 'Favourites', f[0]))
	for t in torrents.find():
		favs = what_favourites(t)
		if favs:
			create_symlinks(t)
	#create_tagsmeta()
	exit(0)



if options.rebuild and options.libdir:
	try:
		shutil.rmtree(options.libdir)
	except:
		print "Could not remove lib dir"
		False
	init_folders()
	for t in torrents.find():
		create_symlinks(t)
	create_tagsmeta()
	exit(0)




if not cookies and not options.password:
	options.password = getpass("Password: ")

try:
	apihandle = whatapi.WhatAPI(username=options.username, password=options.password, cookies=cookies)
except whatapi.whatapi.LoginException:
	print "Login failed"
	exit(-1)

pickle.dump(apihandle.session.cookies, open('.cookies', 'wb'))


init_folders()


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
				
			
			

			if not whatcd_torrent:
				continue
			
			
			if torrents.find_one({'info_hash': info_hash}):
				continue
			
			t_a = datetime.datetime.now()
			
			result = apihandle.request('torrent', hash=info_hash)
			if result['status'] == "success":
				torrents.insert_one({'info_hash': info_hash, 'name': name, 'torrent_info': result['response']})
				t = torrents.find_one({'info_hash': info_hash})
				create_symlinks(t)
				print name + " added"
			else:
				print "Error: "+result['status']
			
			
			t_b = datetime.datetime.now()
			t_c = t_b-t_a
			
			print str(t_c.seconds + t_c.microseconds/1000000.) + " seconds"
			
			if (t_c.seconds*1000000 + t_c.microseconds) > options.interval*1000000:
				sleep((1./(options.interval*1000))-(1./(t_c.seconds*1000 + t_c.microseconds/1000.)))
			

create_tagsmeta()
