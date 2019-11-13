.. _pyatv-testing:

Testing
=======
To ensure good code quality and regression over time, testing is an important
part of pyatv. Mainly two types of tests are used: unit tests and functional
tests. Unit tests are used to verify small independent modules, like the DMAP
parser or conversion methods. The functional tests on the other hand, verifies
that the overall functionality works by using the public API.

When implementing new functionality or fixing bugs, new tests should be written.
Preferably before the actual implementation (test first). Only trivial pull
requests (like pydoc updates or style changes) will be accepted if tests are
missing.

Unit Testing
------------
Regular unit tests should be implemented when adding new (internal)
functionality with a specific purpose, like a parser or converter. These
components are usually small and seldom change their external interface. When
testing a specific function, e.g. pressing "play" or fetching metadata, write
a functional test instead. This allows for greater flexibility when refactoring
since the API is not tied to the implementation too much.

Take look at other tests to get some inspiration, they are all in in the
``tests`` directory.

Functional Testing
------------------

A simple overview of the functional tests setup looks like this: ::


     +-----------------+                +-----------------------+
     |                 | video_playing  |                       |
     |    Test case    |--------------->|    AppleTVUseCases    |
     |                 |                |                       |
     +--------+--------+                +-----------------------+
              ^                   	            |
              | metadata.playing()                  |
              v               	  	            |
       +-------------+        	  	            |
       |             |        	  	            |
       |    pyatv    |        	  	            |
       |             |        	  	            |
       +-------------+        	  	            |
              ^                   	            |
              | DAAP/DMAP                  	    |
              v                   	            |
    +-------------------+         	            |
    |                   |      configure video      |
    |    FakeAppleTV    |<--------------------------+
    |                   |
    +-------------------+

Explanation of each box above:

* **Test case**: This is the actual test case. It uses (only) the public API of
  pyatv and verifies that the response is correct. Implementation wise it's an
  AioHTTPTestCase (basically a regular python unittest, but async). It will
  create an application based on *FakeAppleTV* (below) and a webserver for it,
  that will only be accessible on localhost at a randomized port. This is what
  pyatv communicates with.
* **pyatv**: What is being tested, which is this library. Only the public API
  must be used.
* **FakeAppleTV**: In order to test the library, it must have an Apple TV to
  communicate with. So, FakeAppleTV simulates the behavior of a real device by
  listening on the correct port (on localhost) and answers to DAAP requests.
  To modify what is returned by the fake device, usescases are used.
* **AppleTVUseCases**: Since tests want to verify different kinds of behavior,
  the fake device must be set up accordingly. To make this more abstract from
  the test, usescases are used and this helper realizes the usecases. Instead
  of having to know what different requests should return when for instance
  video is playing, just use the "video usecase".

Simple Example
^^^^^^^^^^^^^^
To get a feeling of how a functional test looks like, have a look at this
example (boiler plate code for creating a device is done during setup):

.. code:: python

    @unittest_run_loop
    def test_metadata_none_type_when_not_playing(self):
        self.usecase.nothing_playing()

        playing = yield from self.atv.metadata.playing()
        self.assertEqual(playing.media_type, const.MEDIA_TYPE_UNKNOWN)
        self.assertEqual(playing.play_state, const.PLAY_STATE_NO_MEDIA)

It's easy to see that the usecase *nothing_playing* is used, which configures
the fake device in such a way that nothing is playing. Metadata is then
fetched with the regular public API and verified to be correct. Most test
cases look like this, which make them easy to understand.
