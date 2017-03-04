.. _pyatv-pairing:

Pairing with a device
=====================
An alternative to using home sharing and the ``HSGID`` identifier is to pair
with the device and use a ``pairing guid`` instead. This is useful if you
for some reason do not want to set up home sharing or if you do not have an
Apple account.

The library automatically handles both types of identifiers. Once you have one
of them, it should just work. So, from now on the term ``login id`` will be
used, which can be either a HSGID or pairing guid.

How does it work
----------------
Pairing with a device is sort of a reversed process compared to when sending
commands to it. The Apple TV listens to a specific Bonjour service with type
``_touch-remote._tcp.local.`` and all remote controls publishes this service.
Included in this service is a bunch of data that is needed for the pairing
process:

* IP-address of the host (remote control)
* A TCP-port open on the host
* Various properties, like the remote name and the pairing guid to be used

When pyatv publishes this service, it might look something like this:

.. code::

    ServiceInfo(type='_touch-remote._tcp.local.',
                name='0000000000000000000000000000000000000001._touch-remote._tcp.local.',
                address=b'\n\x00\n\x19',
                port=57469,
                weight=0,
                priority=0,
                server='0000000000000000000000000000000000000001._touch-remote._tcp.local.',
                properties={
		    b'DvNm': b'pyatv',
                    b'txtvers': b'1',
                    b'RemV': b'10000',
                    b'Pair': b'0000000000000001',
                    b'DvTy': b'iPod',
                    b'RemN': b'Remote'
                }
    )

Note the ``port``, ``DvNM`` (name of the remote) and ``Pair``. These are the
most interesting parameters.

When this service is published, a new remote will "popup" on the Apple TV.
Next is the actual pairing, which is the tricky part. To avoid sending
the pin code over the network (which would eliminate integrity all together),
it instead generates a MD5 hash based on the Pair property and the PIN you
manuelly entered on scren. In case of pyatv, the "algorithm" is:

.. code:: python

    hash = md5(Pair + pin)

It then connects to the port on the host (remote control) and performs a GET
request, including this hash as well as a service name. An example might look
like this:

.. code::

    INFO: 10.0.10.22 - - [04/Feb/2017:15:26:29 +0000] "GET /pair?pairingcode=AAB15DF9F73AA252A7934E0AF9C86B13&servicename=AAAAAAAAAAAAAAAA HTTP/1.1" 200 49 "-" "AppleTV/7.2.2 iOS/8.4.2 AppleTV/7.2.2 model/AppleTV3,1 build/12H606 (3; dt:12)"

The remote control then calculates the hash in the same way and verifies if
it is correct. Of course, the remote decides if the pairing should succeed so
this verification can be skipped altogether to allow any PIN code.

After verifying the hash, a response must be sent sent back to the device.
It is DAAP data and looks like this:

.. code::

    cmpa: [container, dacp.pairinganswer]
      cmpg: 1 [uint, dacp.pairingguid]
      cmnm: pyatv remote [str, dacp.devicename]
      cmty: ipod [str, dacp.devicetype]

As can be seen, the name to be used for the remote is included in the response.
The pairing guid represented as an integer (``0000000000000001`` -> ``1``) is
also included in ``cmpg``. After this response, the pairing process is complete
and ``0000000000000001`` can be used as login id when sending commands to the
device.

.. note::

   If a different pairing guid is used, that should be used as ``login_id``
   instead of ``0000000000000001`` (which is just an example).

Code Example: Pairing
---------------------
When performing pairing, the application is responsible for starting and stopping
the process. In practice this means publishing the Bonjour service, starting the
web server and the opposite. This is done using a
:py:class:`pyatv.pairing.PairingHandler`, which is returned when you call
:py:meth:`pyatv.pair_with_apple_tv`. The process itself is quite simple:

.. code:: python

    import pyatv
    import asyncio
    from zeroconf import Zeroconf

    PIN_CODE = 1234
    REMOTE_NAME = 'my remote control'

    @asyncio.coroutine
    def pair_with_device(loop):
        my_zeroconf = Zeroconf()
        handler = pyatv.pair_with_apple_tv(loop, PIN_CODE, REMOTE_NAME)
	# handler.pairing_guid = '1234ABCDE56789FF'

        yield from handler.start(my_zeroconf)
        yield from asyncio.sleep(60, loop=loop)
        yield from handler.stop()

        if handler.has_paired:
            print('Paired with device!')
	    print('Pairing guid: ' + handler.pairing_guid)
        else:
            print('Did not pair with device!')

        my_zeroconf.close()

    loop = asyncio.get_event_loop()
    loop.run_until_complete(pair_with_device(loop))

By default, a random pairing guid is generated. You can access it with
``handler.pairing_guid`` in order to present it to the user. To change the
pairing guid, you can change this variable to something else *before* calling
``start`` (see above).

This example is available in ``examples``.

References
----------
http://dacp.jsharkey.org/

http://jsharkey.org/blog/2009/06/21/itunes-dacp-pairing-hash-is-broken/
