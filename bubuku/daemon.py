#!/usr/bin/env python3
"""General Kafka Start Script."""

import logging

from bubuku import health
from bubuku.amazon import Amazon
from bubuku.broker import BrokerManager
from bubuku.config import load_config, KafkaProperties
from bubuku.controller import Controller
from bubuku.features.rebalance import RebalanceOnStartCheck, RebalanceOnBrokerListChange
from bubuku.features.rebalance_by_size import RebalanceBySize, GenerateDataSizeStatistics
from bubuku.features.restart_if_dead import CheckBrokerStopped
from bubuku.features.restart_on_zk_change import CheckExhibitorAddressChanged
from bubuku.features.terminate import register_terminate_on_interrupt
from bubuku.id_generator import get_broker_id_policy
from bubuku.utils import CmdHelper
from bubuku.zookeeper import load_exhibitor_proxy, BukuExhibitor
from bubuku.zookeeper import BukuExhibitor, load_exhibitor_proxy

_LOG = logging.getLogger('bubuku.main')


def apply_features(features: str, controller: Controller, buku_proxy: BukuExhibitor, broker: BrokerManager,
                   kafka_properties: KafkaProperties, amazon: Amazon) -> list:
    for feature in set(features.split(',')):
        if feature == 'restart_on_exhibitor':
            controller.add_check(CheckExhibitorAddressChanged(buku_proxy, broker))
        elif feature == 'rebalance_on_start':
            controller.add_check(RebalanceOnStartCheck(buku_proxy, broker))
        elif feature == 'rebalance_on_brokers_change':
            controller.add_check(RebalanceOnBrokerListChange(buku_proxy, broker))
        elif feature == 'rebalance_by_size':
            controller.add_check(GenerateDataSizeStatistics(buku_proxy, broker, CmdHelper(),
                                                            kafka_properties.get_property("log.dirs").split(",")))
            controller.add_check(RebalanceBySize(buku_proxy, broker))
        elif feature == 'graceful_terminate':
            register_terminate_on_interrupt(controller, broker)
        elif feature == 'use_ip_address':
            kafka_properties.set_property('advertised.host.name', amazon.get_own_ip())
        else:
            _LOG.error('Using of unsupported feature "{}", skipping it'.format(feature))


def main():
    logging.basicConfig(level=getattr(logging, 'INFO', None))

    config = load_config()
    _LOG.info("Using configuration: {}".format(config))
    kafka_properties = KafkaProperties(config.kafka_settings_template,
                                       '{}/config/server.properties'.format(config.kafka_dir))

    amazon = Amazon()

    _LOG.info("Loading exhibitor configuration")
    buku_proxy = load_exhibitor_proxy(amazon.get_addresses_by_lb_name(config.zk_stack_name), config.zk_prefix)

    _LOG.info("Loading broker_id policy")
    broker_id_manager = get_broker_id_policy(config.id_policy, buku_proxy, kafka_properties, amazon)

    _LOG.info("Building broker manager")
    broker = BrokerManager(config.kafka_dir, buku_proxy, broker_id_manager, kafka_properties)

    _LOG.info("Creating controller")
    controller = Controller(broker, buku_proxy, amazon)

    controller.add_check(CheckBrokerStopped(broker, buku_proxy))

    apply_features(config.features, controller, buku_proxy, broker, kafka_properties, amazon)

    _LOG.info('Starting health server')
    health.start_server(config.health_port)

    _LOG.info('Starting main controller loop')
    controller.loop()


if __name__ == '__main__':
    main()
