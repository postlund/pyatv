---
layout: template
title: Testing
permalink: /internals/testing
link_group: internals
---
# :ok_hand: Table of Contents
{:.no_toc}
* TOC
{:toc}

# Testing

Testing is an important part of pyatv and there are a lots of tests. The intention is not to have full test coverage, i.e. 100% line coverage (since branch coverage is not supported). The reasoning behind this is that it costs too much when it comes to maintaining the tests and the benefits too low. This does *not* mean that it is OK to not test, it just means that some parts might be easier to inspect manually rather than writing tests for. If the code is easy to test, it should be tested!

*NB: Tests are being re-written to `pytest`-like tests, instead of using regular `unittest` tests. You might see a mix of variants until the work is done, see [#443](https://github.com/postlund/pyatv/issues/443).*

# Running Tests

For running tests, please see [Development Environment](Development-Environment#testing-changes).

# Test Structure

All tests reside in `tests` and follow the same structure as in the code directory (`pyatv/`). `AirPlay` tests can for instance be found in `tests/airplay`. Most tests are regular unit tests, but there are also functional tests that tests pyatv on interface level (see [Types of Tests](#types-of-tests) for more details). They have `functional` in their file names:

| File name | Test Suite |
| --------- | ---------- |
| `tests/common_functional_tests.py` | Common tests that are *identical* to all protocols (i.e. inherited)
| `tests/companion/test_companion_functional.py` | Functional tests for `Companion`
| `tests/dmap/test_dmap_functional.py` | Functional tests for `DMAP`
| `tests/mrp/test_mrp_functional.py` | Functional tests for `MRP`
| `tests/raop/test_raop_functional.py` | Functional tests for `RAOP`
| `tests/support/test_mdns_functional.py` | Functional tests for MDNS
| `tests/test_scan_functional.py` | Functional tests for scanning routines



Generally, if something protocol specific is to be tested it should be added to the protocol specific test suite. But ideally, as many test cases as possible should be added to `common_functional_tests.py` as this will make sure the interface is identical for all protocols.

## Fake Device and Usecases

Testing on interface level, i.e. using the same interface as a developer using pyatv would, comes with the big benefit of flexibility. It allows for great freedom when changing code internally within pyatv without breaking a lot of tests, so that is why these kinds of tests are preferred. They are called *functional tests* in this context. Some details are however hard to test using functional tests, so unit tests can be used in those cases.

For functional tests to work, pyatv needs something to connect to. For this reason a *fake device* is used. It acts like a real devices, but takes a lot of shortcus, implement limited functionality and are only meant to be compatible with pyatv (for now). The fake device starts web servers or open TCP ports, depending on what the protocol uses and the test then sets everything up and connects to it. It short, it looks a bit like this:

```python
    async def setUpAsync(self):
        await super().setUpAsync()
        self.conf = AppleTV(IPv4Address("127.0.0.1"), "Test device")
        self.conf.add_service(
            MrpService("mrp_id", self.fake_atv.get_port(Protocol.MRP))
        )
        self.conf.add_service(
            AirPlayService("airplay_id", self.server.port, DEVICE_CREDENTIALS)
        )
        self.atv = await self.get_connected_device()

    async def get_application(self, loop=None):
        self.fake_atv = FakeAppleTV(self.loop)
        self.state, self.usecase = self.fake_atv.add_service(Protocol.MRP)
        self.airplay_state, self.airplay_usecase = self.fake_atv.add_service(
            Protocol.AirPlay
        )
        return self.fake_atv.app

    async def get_connected_device(self):
        return await pyatv.connect(self.conf, loop=self.loop)
```

The fake device is assigned to `self.fake_atv` and can be used to for instance get some internal state, like the last pressed button. Notice that `pyatv.connect` is used to connect to it. Also notice that scanning is not tested by the functional tests. There are other tests, that stubs zeroconf, for that.

Another concept that is introduced here is `usecase`. A usecase is used to alter the state of a fake device, with some level of abstraction. So instead of modifying the fake device directly, a usecase can be used to for instance change what is currently playing:

```python
    @unittest_run_loop
    async def test_metadata_video_paused(self):
        self.usecase.video_playing(
            paused=True, title="dummy", total_time=100, position=3
        )

        with faketime("pyatv", 0):
            playing = await self.playing(title="dummy")
            self.assertEqual(playing.media_type, MediaType.Video)
            self.assertEqual(playing.device_state, DeviceState.Paused)
            self.assertEqual(playing.title, "dummy")
            self.assertEqual(playing.total_time, 100)
            self.assertEqual(playing.position, 3)
```

Here the fake device is configured to play video with some properties set. The properties are then fetched via the public interface and verified. There are other usecases as well, just look at the implementations. Keeping this abstractions makes it a lot easier to write tests that are shared amongst protocol and is also easier to read. Please note that there's currently no explicit usecase "interface", so it's tricky to see which usescases are shared between all protocols. This would be nice to improve in the future...

Previously one fake device existed per protocol. This has been changed to one fake device that can support multiple services (protocols) instead. To add a service to a fake device, call `add_service`. The state and usecase object for that service will be returned.

Also, there are two new concepts introduced here: polling for a state (`await self.playing(...)`) and `faketime`. These are covered next.

## Illustration of Functional Tests

Here is a simple illustration of how to think of a functional test case:

```raw
     +-----------------+                +-----------------------+
     |                 | video_playing  |                       |
     |    Test case    |--------------->|    AppleTVUseCases    |
     |                 |                |                       |
     +--------+--------+                +-----------------------+
              ^                                     |
              | metadata.playing()                  |
              v                                     |
       +-------------+                              |
       |             |                              |
       |    pyatv    |                              |
       |             |                              |
       +-------------+                              |
              ^                                     |
              | DMAP/AirPlay/MRP/...                |
              v                                     |
    +-------------------+                           |
    |                   |      configure video      |
    |    FakeAppleTV    |<--------------------------+
    |                   |
    +-------------------+
```

## Polling Active State

Because the fake devices uses regular communication protocols, like TCP and HTTP, there are delays in the system. It takes time for messages to be exchanged and everything to be updated correctly, so it's not always possible to assert values like in normal unit tests. Because of this the tests will have to poll the fake device until some expected state is reached. Here is an example:

```python
    @unittest_run_loop
    async def test_button_up(self):
        await self.atv.remote_control.up()
        await until(lambda: self.fake_atv.last_button_pressed == "up")
```

The `up` button is pressed and `self.fake_atv.last_button_pressed` is polled using `await until`, until the correct button is set. The `until` function just calls the provided function until it returns `True`, with a short sleep between each call and a timeout (5s). There's also a convenience method for polling the playing state:

```python
    @unittest_run_loop
    async def test_seek_in_playing_media(self):
        self.usecase.video_playing(
            paused=False, title="dummy", total_time=40, position=10
        )

        with faketime("pyatv", 0):
            await self.atv.remote_control.set_position(30)
            playing = await self.playing(position=30)
            self.assertEqual(playing.position, 30)
```

Awaiting `self.playing` will continue fetching `self.atv.metadata.playing` and verify that all the provided properties have the specified value. Here, it will continue to poll until `position` is set to 30. The corresponding `interface.Playing` object with all information is returned to simplify further investigation.

## Fake Time

Due to `MRP` using real time to calculate current position, time has to be faked. Basically current position is calculated according to `current_time - time_when_something_started_to_play`. I will have to do a better write-up here later, but just use `with faketime("pyatv", 0):` and you'll be fine...

# Types of Tests

Summary of types of tests in pyatv.

## Unit Tests

For simple standalone modules, consider writing unit tests. Write them `pytest`-style. You can then just write some functional tests when integrating it (usually one or a few is enough), to make sure it works with rest of pyatv.

## Functional Tests

When adding features, focus on adding testing on interface level, i.e. write *functional tests*. In the functional tests and extend the fake device to support whatever function you need. The
test case will automatically set the fake device up and make pyatv connect to it, so you can access the public interface. A simple test case might look like this:

```python
@unittest_run_loop
async def test_button_previous(self):
    await self.atv.remote_control.previous()
    await until(lambda: self.fake_atv.last_button_pressed == "previtem")
```

The `previous` button is called with pyatv and the fake device is polled until the button is pressed. Polling is needed because communication is done over TCP, just like with a real device. So it takes some time before the event loop has processed everything. More on this later.
