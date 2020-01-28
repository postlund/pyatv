"""Functional tests for unicast DNS."""

import unittest
import asynctest

from pyatv import udns
from tests import fake_udns


MEDIAREMOTE_SERVICE = '_mediaremotetv._tcp.local'

TEST_SERVICES = {
  MEDIAREMOTE_SERVICE: fake_udns.FakeDnsService(
    name='Kitchen',
    port=1234,
    properties={
      'Name': 'Kitchen',
      'foo': '=bar',
    }),
}


def get_qtype(messages, qtype):
    for message in messages:
        if message.qtype == qtype:
            return message
    return None


class UdnsTest(unittest.TestCase):

    # This is a bastard test for the sake of testing labels (so I don't have to
    # implement it in the fake UDNS server).
    def test_qname_with_label(self):
        # This should resolve to "label.test" when reading from \x05
        message = b'aaaa' + b'\x04test\x00' + b'\x05label\xC0\x04\xAB\xCD'
        ptr = message[10:]
        ret, rest = udns.qname_decode(ptr, message)
        self.assertEqual(ret, 'label.test')
        self.assertEqual(rest, b'\xAB\xCD')


class UdnsFunctionalTest(asynctest.TestCase):

    async def setUp(self):
        self.server = fake_udns.FakeUdns(self.loop, TEST_SERVICES)
        await self.server.start()

    async def request(self, service_name):
        return await udns.request(
            self.loop, '127.0.0.1', [service_name], port=self.server.port,
            timeout=1), TEST_SERVICES.get(service_name)

    async def test_non_existing_service(self):
        resp, _ = await self.request('_missing')
        self.assertEqual(len(resp.questions), 1)
        self.assertEqual(len(resp.answers), 0)
        self.assertEqual(len(resp.resources), 0)

    async def test_service_has_expected_responses(self):
        resp, _ = await self.request(MEDIAREMOTE_SERVICE)
        self.assertEqual(len(resp.questions), 1)
        self.assertEqual(len(resp.answers), 1)
        self.assertEqual(len(resp.resources), 2)

    async def test_service_has_valid_question(self):
        resp, _ = await self.request(MEDIAREMOTE_SERVICE)

        question = resp.questions[0]
        self.assertEqual(question.qname, MEDIAREMOTE_SERVICE)
        self.assertEqual(question.qtype, udns.QTYPE_ANY)
        self.assertEqual(question.qclass, 0x8001)

    async def test_service_has_valid_answer(self):
        resp, data = await self.request(MEDIAREMOTE_SERVICE)

        answer = resp.answers[0]
        self.assertEqual(answer.qname, MEDIAREMOTE_SERVICE)
        self.assertEqual(answer.qtype, udns.QTYPE_PTR)
        self.assertEqual(answer.qclass, fake_udns.DEFAULT_QCLASS)
        self.assertEqual(answer.ttl, fake_udns.DEFAULT_TTL)
        self.assertEqual(answer.rd, data.name + '.' + MEDIAREMOTE_SERVICE)

    async def test_service_has_valid_srv_resource(self):
        resp, data = await self.request(MEDIAREMOTE_SERVICE)

        srv = get_qtype(resp.resources, udns.QTYPE_SRV)
        self.assertEqual(srv.qname, data.name + '.' + MEDIAREMOTE_SERVICE)
        self.assertEqual(srv.qtype, udns.QTYPE_SRV)
        self.assertEqual(srv.qclass, fake_udns.DEFAULT_QCLASS)
        self.assertEqual(srv.ttl, fake_udns.DEFAULT_TTL)

        rd = srv.rd
        self.assertEqual(rd['priority'], 0)
        self.assertEqual(rd['weight'], 0)
        self.assertEqual(rd['port'], data.port)
        self.assertEqual(rd['target'], data.name + '.local')

    async def test_service_has_valid_txt_resource(self):
        resp, data = await self.request(MEDIAREMOTE_SERVICE)

        srv = get_qtype(resp.resources, udns.QTYPE_TXT)
        self.assertEqual(srv.qname, data.name + '.' + MEDIAREMOTE_SERVICE)
        self.assertEqual(srv.qtype, udns.QTYPE_TXT)
        self.assertEqual(srv.qclass, fake_udns.DEFAULT_QCLASS)
        self.assertEqual(srv.ttl, fake_udns.DEFAULT_TTL)

        rd = srv.rd
        self.assertEqual(len(rd), len(data.properties))
        for k, v in data.properties.items():
            self.assertEqual(rd[k.encode('ascii')],
                             v.encode('ascii'))
