#!/usr/bin/env python

import os
import sys
sys.path.insert(0, os.path.abspath('..'))
import CloudFlare

import re
import json
import requests

def my_ip_address():
	# This list is adjustable - plus some v6 enabled services are needed
	# url = 'http://myip.dnsomatic.com'
	# url = 'http://www.trackip.net/ip'
	# url = 'http://myexternalip.com/raw'
	url = 'https://api.ipify.org'
	try:
		ip_address = requests.get(url).text
	except:
		exit('%s: failed' % (url))
	if ip_address == '':
		exit('%s: failed' % (url))

	if ':' in ip_address:
		ip_address_type = 'AAAA'
	else:
		ip_address_type = 'A'

	return ip_address, ip_address_type

def main():
	try:
		dns_name = sys.argv[1]
	except:
		exit('usage: example-update-dynamic-dns.py fqdn-hostname')

	host_name, zone_name = dns_name.split('.', 1)

	ip_address, ip_address_type  = my_ip_address()

	print 'MY IP: %s %s' % (dns_name, ip_address)

	cf = CloudFlare.CloudFlare()

	# grab the zone identifier
	try:
		params = {'name':zone_name}
		zones = cf.zones.get(params=params)
	except CloudFlare.CloudFlareAPIError as e:
		exit('/zones %d %s - api call failed' % (e, e))
	except Exception as e:
		exit('/zones.get - %s - api call failed' % (e))

	if len(zones) != 1:
		exit('/zones.get - %s - api call returned %d items' % (zone_name, len(zones)))

	zone = zones[0]

	zone_name = zone['name']
	zone_id = zone['id']

	try:
		params = {'name':dns_name,'match':'all','type':ip_address_type}
		dns_records = cf.zones.dns_records.get(zone_id, params=params)
	except CloudFlare.CloudFlareAPIError as e:
		exit('/zones/dns_records %s - %d %s - api call failed' % (dns_name, e, e))

	did_update = False

	# update the record - unless it's already correct
	for dns_record in dns_records:
		old_ip_address = dns_record['content']
		old_ip_address_type = dns_record['type']

		if ip_address_type not in ['A', 'AAAA']:
			# we only deal with A / AAAA records
			continue

		if ip_address_type != old_ip_address_type:
			# only update the correct address type (A or AAAA)
			print 'IGNORED: %s %s ; wrong address family' % (dns_name, old_ip_address)
			continue

		if ip_address == old_ip_address:
			print 'UNCHANGED: %s %s' % (dns_name, ip_address)
			did_update = True
			continue

		dns_record_id = dns_record['id']
		# update this record - we know it's the same address type
		dns_record = {
			'name':dns_name,
			'type':ip_address_type,
			'content':ip_address
		}
		try:
			dns_record = cf.zones.dns_records.put(zone_id, dns_record_id, data=dns_record)
		except CloudFlare.CloudFlareAPIError as e:
			exit('/zones.dns_records.put %s - %d %s - api call failed' % (dns_name, e, e))
		print 'UPDATED: %s %s -> %s' % (dns_name, old_ip_address, ip_address)
		did_update = True

	if did_update == False:
		# nothing found - so create record
		dns_record = {
			'name':host_name,
			'type':ip_address_type,
			'content':ip_address
		}
		try:
			dns_record = cf.zones.dns_records.post(zone_id, data=dns_record)
		except CloudFlare.CloudFlareAPIError as e:
			exit('/zones.dns_records.post %s - %d %s - api call failed' % (dns_name, e, e))
		print 'CREATED: %s %s' % (dns_name, ip_address)
		exit(0)

if __name__ == '__main__':
	main()

