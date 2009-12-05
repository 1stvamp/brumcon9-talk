"""minifb, Minimal facebook api.
Stateless functions to access the facebook api.
Version 1.2
October 27, 2009
Peter Shinners

The documentation for the Facebook methods and arguments and return
values is well written. http://developers.facebook.com/documentation.php

This was developed on Python 2.4, but should easily run on other versions.

By default this requires the 'simplejson' module. But if requesting
raw text in XML or JSON modes then it is not used or imported.
http://cheeseshop.python.org/pypi/simplejson

This code is released under the MIT license.


# Examples of usage
import minifb
_FbApiKey = "xxxyyyzzz..."
_FbSecret = minifb.FacebookSecret("aaabbbccc...")


def ModPythonHandler(request):
    '''FBML Canvas page receives session info from POST'''
    arguments = minifb.validate(_FbSecret, request.read())
    if arguments["added"] != "1":
        return ServeIndexNonmember()
    else:
        session_key = arguments["session_key"]
        uid = arguments["user"]
        return ServeIndex(uid, session_key)


def UserAdded(request):
    '''Facebook callback when user has added application
        gets an auth_token through post that must be converted
        into a session_key. Then lookup and send stuff to Facebook'''
    # Parse and validate posted values
    arguments = minifb.validate(_FbSecret, request.read())
    auth_token = arguments["auth_token"]
    
    # Request session_key from auth_token
    result = minifb.call("facebook.auth.getSession",
                _FbApiKey, _FbSecret, auth_token=auth_token)
    uid = result["uid"]
    session_key = result["session_key"]

    # Lookup username and details
    usersInfo = minifb.call("facebook.users.getInfo",
                    _FbApiKey, _FbSecret, session_key=session_key,
                    call_id=True, fields="name,pic_square",
                    uids=uid) # uids can be comma separated list
    name = usersInfo[0]["name"]
    photo = usersInfo[0]["pic_square"]
    
    AddUserToDatabase(uid, name, photo)

    # Set the users profile FBML
    fbml = "<p>Welcome, new user, <b>%s</b></p>" % name
    minifb.call("facebook.profile.setFBML",
                _FbApiKey, _FbSecret, session_key=session_key,
                call_id=True, uid=uid, markup=fbml)

"""


# Copyright (c) 2009 Peter Shinners

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.



__all__ = ["FacebookError", "call", "validate", "FacebookSecret"]



# Attempt Python3 style imports. Fallback on Python2
import sys
import cgi

try:
    # Python 3 setup
    from hashlib import md5
    from urllib.parse import urlencode
    from urllib.request import urlopen
    from urllib.error import URLError
    StandardError = Exception
    def buffer(value):
        if isinstance(value, str):
            return memoryview(value.encode())
        return memoryview(value)
    
except ImportError:
    # Python 2 setup
    from md5 import md5
    from urllib import urlencode
    from urllib2 import urlopen
    from urllib2 import URLError



# Globals
_fbUrl = "http://api.facebook.com/restserver.php"
_fbApi = "1.0"
_fbCallCounter = 1



class FacebookError(StandardError):
    """Error that happens during a facebook call."""
    def __init__(self, error_code, error_msg):
        self.error_code = error_code
        self.error_msg = error_msg
        StandardError.__init__(self, "Facebook Error %s: %s"
                    % (self.error_code, self.error_msg))



def call(method, api_key, secret, **kwargs):
    """Call facebook server with a method request. Most keyword arguments
        are passed directly to the server with a few exceptions.
        The 'sig' value will always be computed automatically.
        The 'v' version will be supplied automatically if needed.
        The 'call_id' defaults to True, which will generate a valid
        number. Otherwise it should be a valid number or False to not send.

        The default return is a parsed simplejson object.
        Unless the 'format' and/or 'callback' arguments are given,
        in which case the raw text of the reply is returned. The string
        will always be returned, even during errors.

        If an error occurs, a FacebookError exception will be raised
        with the proper code and message.
        
        The secret argument can be any string, but should be an
        instance of FacebookSecret to hide value from simple
        introspection.
        """
    # Finalize kwargs
    call_id = kwargs.get("call_id", True)
    if call_id is True:
        # GIL helps this be 99% thread safe, but this could be trouble?
        global _fbCallCounter
        _fbCallCounter += 1
        kwargs["call_id"] = _fbCallCounter
    elif call_id is False:
        del kwargs["call_id"]
    customFormat = "format" in kwargs or "callback" in kwargs
    kwargs.setdefault("format", "JSON")
    kwargs.setdefault("v", _fbApi)
    kwargs.setdefault("api_key", api_key)
    kwargs.setdefault("method", method)

    # Hash with secret key
    md5hash = md5()
    for key, value in sorted(kwargs.items()):
        md5hash.update(key)
        md5hash.update("=")
        md5hash.update(str(value))
    md5hash.update(_Hashable(secret))
    del secret  # No longer using secret, clear it from locals
    kwargs["sig"] = md5hash.hexdigest()

    # Call website, send arguments as POST
    args = urlencode(kwargs)  # should pass doseq=True?
    try:
        response = urlopen(_fbUrl, args).read()
    except URLError:
        msg = str(sys.exc_info())[-1]
        raise IOError("The facebook server is down. " + msg)

    # Handle response
    if customFormat:
        return response
    
    import simplejson
    data = simplejson.loads(response)
    try:
        raise FacebookError(data["error_code"], data["error_msg"])
    except (LookupError, TypeError):
        pass
    return data



def validate(secret, arguments):
    """Validate the arguments received from facebook. This is usually
        sent for the iframe in Facebook's canvas. It is not necessary
        to use this on the auth_token and uid passed to callbacks like
        post-add and post-remove.

        The arguments must be a mapping of to string keys and values
        or a string of http request data. The returned dictionary 
        will only contain the signed values from the arguments.
        If the data is invalid or not signed properly, and empty
        dictionary is returned.
        
        The secret argument can be any string, but should be an
        instance of FacebookSecret to hide value from simple
        introspection and tracebacks.
        """
    # Convert argument types into a plain dictionary
    try:
        values = dict(arguments.items())
    except (AttributeError, ValueError):
        values = dict(cgi.parse_qs(arguments))

    signature = values.pop("fb_sig", None)
    if not signature:
        return {}

    # Hash data with secret key
    prefix = "fb_sig_"
    preflen = len(prefix)
    
    signed = []
    for (i, j) in values.items():
        if i.startswith(prefix):
            signed.append((i[preflen:], j))
    signed.sort()

    md5hash = md5()
    for key, value in signed:
        md5hash.update(key)
        md5hash.update("=")
        md5hash.update(_Hashable(value))
    md5hash.update(_Hashable(secret))
    del secret  # No longer using secret, clear it from locals
    if md5hash.hexdigest() != signature:
        # Hash is incorrect
        return {}

    return dict(signed)


def _Hashable(value):
    """Create a value that can be passed to md5hash. This works to
        convert values that come from FieldStorage, lists, and more
        into the correct string.
        """
    if isinstance(value, FacebookSecret):
        return value.__call__()

    if isinstance(value, list) and len(value) == 1:
        value = value[0]
    try:
        value = buffer(value)
    except TypeError:
        try:
            value = value.value()
        except (AttributeError, TypeError):
            pass
    return value



class FacebookSecret(object):
    """Simple container that stores a secret value. Will prevent fancy
        traceback tools like cgitb and django from showing the secret key
        in error reports.
        
        The static value method will convert this or any object to
        a string.
        """
    def __init__(self, value):
        b = buffer(value)
        del value
        self.__call__ = lambda: b
        # Odd to mask this as a builtin. It doesn't fool vars(), but
        # class instances are still not callable, TypeError.
    
    
    def __str__(self):
        return "<FacebookSecret>"
    __repr__ = __str__

