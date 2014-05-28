import urllib2
import urllib
import cookielib
from HTMLParser import HTMLParser
from urlparse import urlparse
import json

class VkAuthResponceParser(HTMLParser):
	def __init__(self):
		HTMLParser.__init__(self)
		self.url = None
		self.params = {}
		self.in_form = False
		self.form_parsed = False
		self.method = "GET"

	def handle_starttag(self, tag, attrs):
		tag = tag.lower()
		if tag == "form":
			if self.form_parsed:
				raise RuntimeError("Second form on page")
			if self.in_form:
				raise RuntimeError("Already in form")
			self.in_form = True
		if not self.in_form:
			return
		attrs = dict((name.lower(), value) for name, value in attrs)
		if tag == "form":
			self.url = attrs["action"]
			if "method" in attrs:
				self.method = attrs["method"].upper()
		elif tag == "input" and "type" in attrs and "name" in attrs:
			if attrs["type"] in ["hidden", "text", "password"]:
				self.params[attrs["name"]] = attrs["value"] if "value" in attrs else ""

	def handle_endtag(self, tag):
		tag = tag.lower()
		if tag == "form":
			if not self.in_form:
				raise RuntimeError("Unexpected end of <form>")
			self.in_form = False
			self.form_parsed = True

class VK:
	def  __init__(self):
		print("vk created")
		self.access_token = ""
		self.user_id = ""
		self.client_id = 2951857 # TODO: register our vk app
		self.scope = '8'

	def auth(self, email, password):
		
		def split_key_value(kv_pair):
			kv = kv_pair.split("=")
			return kv[0], kv[1]

		# Authorization form
		def auth_user(email, password, opener):
			response = opener.open(
				"http://oauth.vk.com/oauth/authorize?" + \
				"redirect_uri=http://oauth.vk.com/blank.html&response_type=token&" + \
				"client_id=%s&scope=%s&display=wap" % (self.client_id, ",".join(self.scope))
				)
			doc = response.read()
			parser = VkAuthResponceParser()
			parser.feed(doc)
			parser.close()
			if not parser.form_parsed or parser.url is None or "pass" not in parser.params or \
			  "email" not in parser.params:
				  raise RuntimeError("Something wrong")
			parser.params["email"] = email
			parser.params["pass"] = password
			if parser.method == "POST":
				response = opener.open(parser.url, urllib.urlencode(parser.params))
			else:
				raise NotImplementedError("Method '%s'" % parser.method)
			return response.read(), response.geturl()

		# Permission request form
		def give_access(doc, opener):
			parser = VkAuthResponceParser()
			parser.feed(doc)
			
			parser.close()
			if not parser.form_parsed or parser.url is None:
				  raise RuntimeError("Something wrong")
			if parser.method == "POST":
				response = opener.open(parser.url, urllib.urlencode(parser.params))
			else:
				raise NotImplementedError("Method '%s'" % parser.method)
			return response.geturl()

		opener = urllib2.build_opener(
			urllib2.HTTPCookieProcessor(cookielib.CookieJar()),
			urllib2.HTTPRedirectHandler())
		doc, url = auth_user(email, password, opener)
		if urlparse(url).path != "/blank.html":
			url = give_access(doc, opener)
		if urlparse(url).path != "/blank.html":
			raise RuntimeError("Expected success here")
		answer = dict(split_key_value(kv_pair) for kv_pair in urlparse(url).fragment.split("&"))
		if "access_token" not in answer or "user_id" not in answer:
			raise RuntimeError("Missing some values in answer")
		self.access_token = answer["access_token"];
		self.user_id = answer["user_id"]

	def call_api(self, method, params):
		if isinstance(params, list):
			params_list = [kv for kv in params]
		elif isinstance(params, dict):
			params_list = params.items()
		else:
			params_list = [params]
		params_list.append(("access_token", self.access_token))
		url = "https://api.vk.com/method/%s?%s" % (method, urllib.urlencode(params_list))
		return json.loads(urllib2.urlopen(url).read())["response"]


vk = VK()
email = 'enter your email'
password = 'enter your pass'
try:
	vk.auth(email, password)
	audios = vk.call_api("audio.get", ("uid", vk.user_id))
	for a in audios:
		print(a['title'].encode('utf8'))
		print(a['url'].encode('utf8'))
except RuntimeError as r:
	print("Error:%s"%r.args[0])

