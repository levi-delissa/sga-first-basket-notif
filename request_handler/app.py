#!/usr/bin/env python3

import aws_cdk as cdk

from request_handler.request_handler_stack import RequestHandlerStack


app = cdk.App()
RequestHandlerStack(app, "request-handler")

app.synth()
