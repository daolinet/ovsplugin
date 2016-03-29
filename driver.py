# Copyright 2016 Networks
import logging
import sys
from netaddr import IPAddress, IPNetwork

from flask import Flask, jsonify, request
from werkzeug.exceptions import HTTPException, default_exceptions

import linux_net
from utils import generate_mac
from utils import generate_devname
from utils import ProcessExecutionError

LOCAL_PREFIX = "tap"
REMOTE_PREFIX = "ns"
BRIDGE = "daolinet"

# From http://flask.pocoo.org/snippets/83/
def make_json_app(import_name, **kwargs):
    """
    Creates a JSON-oriented Flask app.

    All error responses that you don't specifically
    manage yourself will have application/json content
    type, and will contain JSON like this (just an example):

    { "message": "405: Method Not Allowed" }
    """
    def make_json_error(ex):
        response = jsonify({"Err": str(ex)})
        response.status_code = (ex.code
                                if isinstance(ex, HTTPException)
                                else 500)
        return response

    app = Flask(__name__, **kwargs)

    for code in default_exceptions.iterkeys():
        app.error_handler_spec[None][code] = make_json_error

    return app

app = make_json_app(__name__)
app.logger.addHandler(logging.StreamHandler(sys.stdout))
app.logger.setLevel(logging.DEBUG)
app.logger.info("Daolinet plugin started")

@app.route('/Plugin.Activate', methods=['POST'])
def activate():
    data = {"Implements": ["NetworkDriver"]}
    app.logger.debug("Activate data %s", data)
    return jsonify(data)

# libnetwork plugin API
@app.route('/NetworkDriver.GetCapabilities', methods=['POST'])
def get_capabilities():
    response = {"Scope": "global"}
    app.logger.debug("Get Capabilities %s", response)
    return jsonify(response)

@app.route('/NetworkDriver.CreateNetwork', methods=['POST'])
def create_network():
    data = request.get_json(force=True)
    app.logger.debug("Create network %s", data)

    network_id = data["NetworkID"]
    dev = generate_devname(LOCAL_PREFIX, network_id)
    ipv4 = data['IPv4Data']
    if len(ipv4) != 1:
        msg = "IPv4Data support only one subnetwork"
        app.logger.error(msg)
        raise Exception(msg)

    gateway = ipv4[0].get('Gateway')
    if not gateway:
        msg = "No available Gateway"
        app.logger.error(msg)
        raise Exception(msg)

    app.logger.debug("Create Network data %s", "{}")
    return jsonify({})

@app.route('/NetworkDriver.DeleteNetwork', methods=['POST'])
def delete_network():
    data = request.get_json(force=True)
    app.logger.debug("Delete network %s", data)
    return jsonify({})

@app.route('/NetworkDriver.CreateEndpoint', methods=['POST'])
def create_endpoint():
    data = request.get_json(force=True)
    app.logger.debug("Create Endpoint %s", data)
    endpoint_id = data["EndpointID"]
    network_id = data["NetworkID"]
    interface = data["Interface"]

    macaddr = generate_mac()
    if_local = generate_devname(LOCAL_PREFIX, endpoint_id)
    if_remote = generate_devname(REMOTE_PREFIX, endpoint_id)

    # Create the veth pair
    linux_net.plugin(if_local, if_remote)

    try:
        linux_net.set_mac(if_remote, macaddr)
    except ProcessExecutionError as e:
        linux_net.delete_net_dev(if_remote)
        raise e

    response = {
        "Interface": {
            "MacAddress": macaddr,
        }
    }
    return jsonify(response)

@app.route('/NetworkDriver.EndpointOperInfo', methods=['POST'])
def endpoint_operinfo():
    data = request.get_json(force=True)
    app.logger.debug("Endpoint OperInfo %s", data)
    endpoint_id = data["EndpointID"]
    response = {
        "Value": {}
    }
    return jsonify(response)

@app.route('/NetworkDriver.DeleteEndpoint', methods=['POST'])
def delete_endpoint():
    data = request.get_json(force=True)
    app.logger.debug("Delete Endpoint %s", data)
    endpoint_id = data["EndpointID"]

    return jsonify({})

@app.route('/NetworkDriver.Join', methods=['POST'])
def join():
    data = request.get_json(force=True)
    app.logger.debug("Join Endpoint %s", data)
    network_id = data["NetworkID"]
    endpoint_id = data["EndpointID"]

    if_local = generate_devname(LOCAL_PREFIX, endpoint_id)
    if_remote = generate_devname(REMOTE_PREFIX, endpoint_id)

    try:
        # Add dev to ovs
        linux_net.create_ovs_port(BRIDGE, if_local)
    except ProcessExecutionError as e:
        linux_net.delete_net_dev(if_remote)
        raise e

    response = {
        "InterfaceName": {
            "SrcName": if_remote,
            "DstPrefix": "eth",
        },
        "Gateway": linux_net.gateway_get(network_id),
    }

    return jsonify(response)

@app.route('/NetworkDriver.Leave', methods=['POST'])
def leave():
    data = request.get_json(force=True)
    app.logger.debug("Leave %s", data)
    endpoint_id = data["EndpointID"]

    dev = generate_devname(LOCAL_PREFIX, endpoint_id)
    linux_net.delete_ovs_port(BRIDGE, dev)
    linux_net.delete_net_dev(dev)
    return jsonify({})

@app.route('/NetworkDriver.DiscoverNew', methods=['POST'])
def discover_new():
    data = request.get_json(force=True)
    app.logger.debug("Discover New %s", data)
    return jsonify({})

@app.route('/NetworkDriver.DiscoverDelete', methods=['POST'])
def discover_delete():
    data = request.get_json(force=True)
    app.logger.debug("Discover Delete %s", data)
    return jsonify({})
