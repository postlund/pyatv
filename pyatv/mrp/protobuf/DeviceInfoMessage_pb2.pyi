# @generated by generate_proto_mypy_stubs.py.  Do not edit!
import sys
from google.protobuf.descriptor import (
    Descriptor as google___protobuf___descriptor___Descriptor,
    FieldDescriptor as google___protobuf___descriptor___FieldDescriptor,
    FileDescriptor as google___protobuf___descriptor___FileDescriptor,
)

from google.protobuf.internal.containers import (
    RepeatedCompositeFieldContainer as google___protobuf___internal___containers___RepeatedCompositeFieldContainer,
    RepeatedScalarFieldContainer as google___protobuf___internal___containers___RepeatedScalarFieldContainer,
)

from google.protobuf.message import (
    Message as google___protobuf___message___Message,
)

from pyatv.mrp.protobuf.Common_pb2 import (
    DeviceClass as pyatv___mrp___protobuf___Common_pb2___DeviceClass,
)

from typing import (
    Iterable as typing___Iterable,
    Optional as typing___Optional,
    Text as typing___Text,
)

from typing_extensions import (
    Literal as typing_extensions___Literal,
)


builtin___bool = bool
builtin___bytes = bytes
builtin___float = float
builtin___int = int


DESCRIPTOR: google___protobuf___descriptor___FileDescriptor = ...

class DeviceInfoMessage(google___protobuf___message___Message):
    DESCRIPTOR: google___protobuf___descriptor___Descriptor = ...
    uniqueIdentifier: typing___Text = ...
    name: typing___Text = ...
    localizedModelName: typing___Text = ...
    systemBuildVersion: typing___Text = ...
    applicationBundleIdentifier: typing___Text = ...
    applicationBundleVersion: typing___Text = ...
    protocolVersion: builtin___int = ...
    lastSupportedMessageType: builtin___int = ...
    supportsSystemPairing: builtin___bool = ...
    allowsPairing: builtin___bool = ...
    connected: builtin___bool = ...
    systemMediaApplication: typing___Text = ...
    supportsACL: builtin___bool = ...
    supportsSharedQueue: builtin___bool = ...
    supportsExtendedMotion: builtin___bool = ...
    bluetoothAddress: builtin___bytes = ...
    sharedQueueVersion: builtin___int = ...
    deviceUID: typing___Text = ...
    managedConfigDeviceID: typing___Text = ...
    deviceClass: pyatv___mrp___protobuf___Common_pb2___DeviceClass.EnumValue = ...
    logicalDeviceCount: builtin___int = ...
    tightlySyncedGroup: builtin___bool = ...
    isProxyGroupPlayer: builtin___bool = ...
    tightSyncUID: typing___Text = ...
    groupUID: typing___Text = ...
    groupName: typing___Text = ...
    isGroupLeader: builtin___bool = ...
    isAirplayActive: builtin___bool = ...
    systemPodcastApplication: typing___Text = ...
    enderDefaultGroupUID: typing___Text = ...
    airplayReceivers: google___protobuf___internal___containers___RepeatedScalarFieldContainer[typing___Text] = ...
    linkAgent: typing___Text = ...
    clusterID: typing___Text = ...
    clusterLeaderID: typing___Text = ...
    clusterType: builtin___int = ...
    isClusterAware: builtin___bool = ...
    modelID: typing___Text = ...

    @property
    def groupedDevices(self) -> google___protobuf___internal___containers___RepeatedCompositeFieldContainer[type___DeviceInfoMessage]: ...

    def __init__(self,
        *,
        uniqueIdentifier : typing___Optional[typing___Text] = None,
        name : typing___Optional[typing___Text] = None,
        localizedModelName : typing___Optional[typing___Text] = None,
        systemBuildVersion : typing___Optional[typing___Text] = None,
        applicationBundleIdentifier : typing___Optional[typing___Text] = None,
        applicationBundleVersion : typing___Optional[typing___Text] = None,
        protocolVersion : typing___Optional[builtin___int] = None,
        lastSupportedMessageType : typing___Optional[builtin___int] = None,
        supportsSystemPairing : typing___Optional[builtin___bool] = None,
        allowsPairing : typing___Optional[builtin___bool] = None,
        connected : typing___Optional[builtin___bool] = None,
        systemMediaApplication : typing___Optional[typing___Text] = None,
        supportsACL : typing___Optional[builtin___bool] = None,
        supportsSharedQueue : typing___Optional[builtin___bool] = None,
        supportsExtendedMotion : typing___Optional[builtin___bool] = None,
        bluetoothAddress : typing___Optional[builtin___bytes] = None,
        sharedQueueVersion : typing___Optional[builtin___int] = None,
        deviceUID : typing___Optional[typing___Text] = None,
        managedConfigDeviceID : typing___Optional[typing___Text] = None,
        deviceClass : typing___Optional[pyatv___mrp___protobuf___Common_pb2___DeviceClass.EnumValue] = None,
        logicalDeviceCount : typing___Optional[builtin___int] = None,
        tightlySyncedGroup : typing___Optional[builtin___bool] = None,
        isProxyGroupPlayer : typing___Optional[builtin___bool] = None,
        tightSyncUID : typing___Optional[typing___Text] = None,
        groupUID : typing___Optional[typing___Text] = None,
        groupName : typing___Optional[typing___Text] = None,
        groupedDevices : typing___Optional[typing___Iterable[type___DeviceInfoMessage]] = None,
        isGroupLeader : typing___Optional[builtin___bool] = None,
        isAirplayActive : typing___Optional[builtin___bool] = None,
        systemPodcastApplication : typing___Optional[typing___Text] = None,
        enderDefaultGroupUID : typing___Optional[typing___Text] = None,
        airplayReceivers : typing___Optional[typing___Iterable[typing___Text]] = None,
        linkAgent : typing___Optional[typing___Text] = None,
        clusterID : typing___Optional[typing___Text] = None,
        clusterLeaderID : typing___Optional[typing___Text] = None,
        clusterType : typing___Optional[builtin___int] = None,
        isClusterAware : typing___Optional[builtin___bool] = None,
        modelID : typing___Optional[typing___Text] = None,
        ) -> None: ...
    def HasField(self, field_name: typing_extensions___Literal[u"allowsPairing",b"allowsPairing",u"applicationBundleIdentifier",b"applicationBundleIdentifier",u"applicationBundleVersion",b"applicationBundleVersion",u"bluetoothAddress",b"bluetoothAddress",u"clusterID",b"clusterID",u"clusterLeaderID",b"clusterLeaderID",u"clusterType",b"clusterType",u"connected",b"connected",u"deviceClass",b"deviceClass",u"deviceUID",b"deviceUID",u"enderDefaultGroupUID",b"enderDefaultGroupUID",u"groupName",b"groupName",u"groupUID",b"groupUID",u"isAirplayActive",b"isAirplayActive",u"isClusterAware",b"isClusterAware",u"isGroupLeader",b"isGroupLeader",u"isProxyGroupPlayer",b"isProxyGroupPlayer",u"lastSupportedMessageType",b"lastSupportedMessageType",u"linkAgent",b"linkAgent",u"localizedModelName",b"localizedModelName",u"logicalDeviceCount",b"logicalDeviceCount",u"managedConfigDeviceID",b"managedConfigDeviceID",u"modelID",b"modelID",u"name",b"name",u"protocolVersion",b"protocolVersion",u"sharedQueueVersion",b"sharedQueueVersion",u"supportsACL",b"supportsACL",u"supportsExtendedMotion",b"supportsExtendedMotion",u"supportsSharedQueue",b"supportsSharedQueue",u"supportsSystemPairing",b"supportsSystemPairing",u"systemBuildVersion",b"systemBuildVersion",u"systemMediaApplication",b"systemMediaApplication",u"systemPodcastApplication",b"systemPodcastApplication",u"tightSyncUID",b"tightSyncUID",u"tightlySyncedGroup",b"tightlySyncedGroup",u"uniqueIdentifier",b"uniqueIdentifier"]) -> builtin___bool: ...
    def ClearField(self, field_name: typing_extensions___Literal[u"airplayReceivers",b"airplayReceivers",u"allowsPairing",b"allowsPairing",u"applicationBundleIdentifier",b"applicationBundleIdentifier",u"applicationBundleVersion",b"applicationBundleVersion",u"bluetoothAddress",b"bluetoothAddress",u"clusterID",b"clusterID",u"clusterLeaderID",b"clusterLeaderID",u"clusterType",b"clusterType",u"connected",b"connected",u"deviceClass",b"deviceClass",u"deviceUID",b"deviceUID",u"enderDefaultGroupUID",b"enderDefaultGroupUID",u"groupName",b"groupName",u"groupUID",b"groupUID",u"groupedDevices",b"groupedDevices",u"isAirplayActive",b"isAirplayActive",u"isClusterAware",b"isClusterAware",u"isGroupLeader",b"isGroupLeader",u"isProxyGroupPlayer",b"isProxyGroupPlayer",u"lastSupportedMessageType",b"lastSupportedMessageType",u"linkAgent",b"linkAgent",u"localizedModelName",b"localizedModelName",u"logicalDeviceCount",b"logicalDeviceCount",u"managedConfigDeviceID",b"managedConfigDeviceID",u"modelID",b"modelID",u"name",b"name",u"protocolVersion",b"protocolVersion",u"sharedQueueVersion",b"sharedQueueVersion",u"supportsACL",b"supportsACL",u"supportsExtendedMotion",b"supportsExtendedMotion",u"supportsSharedQueue",b"supportsSharedQueue",u"supportsSystemPairing",b"supportsSystemPairing",u"systemBuildVersion",b"systemBuildVersion",u"systemMediaApplication",b"systemMediaApplication",u"systemPodcastApplication",b"systemPodcastApplication",u"tightSyncUID",b"tightSyncUID",u"tightlySyncedGroup",b"tightlySyncedGroup",u"uniqueIdentifier",b"uniqueIdentifier"]) -> None: ...
type___DeviceInfoMessage = DeviceInfoMessage

deviceInfoMessage: google___protobuf___descriptor___FieldDescriptor = ...
