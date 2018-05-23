from __future__ import print_function

from yellowant import YellowAnt
import json
from yellowant.messageformat import MessageClass, MessageAttachmentsClass, MessageButtonsClass, AttachmentFieldsClass
from .models import VictorOpsUserToken, YellowUserToken
import traceback
import requests
import datetime
import pytz
from django.conf import settings
import time
import victorops_client
from victorops_client.rest import ApiException
from pprint import pprint
import requests
import re
import numpy as np

class CommandCentre(object):
    def __init__(self, yellowant_user_id, yellowant_integration_id, function_name, args):
        self.yellowant_user_id = yellowant_user_id
        self.yellowant_integration_id = yellowant_integration_id
        self.function_name = function_name
        self.args = args

    def parse(self):
        self.commands = {
            'get_incident': self.get_incident,
            'list_incidents': self.list_incidents,
            'get_user': self.get_user,
            'list_users': self.list_users,
            'create_incident': self.create_incident,
            'add_user': self.add_user,
            'ack_incidents': self.ack_incidents,
            'resolve_incidents': self.resolve_incidents,
            'ack_all_incidents': self.ack_all_incidents,
            'resolve_all_incidents': self.resolve_all_incidents,
        }

        self.user_integration = YellowUserToken.objects.get(yellowant_integration_id=self.yellowant_integration_id)
        self.victor_ops_object = VictorOpsUserToken.objects.get(user_integration=self.user_integration)
        self.victor_ops_uid = self.victor_ops_object.victorops_user_id

        self.headers = {
            'Content-Type': 'application/json', 'X-VO-Api-Id': '90bf5258', 'X-VO-Api-Key': 'f5fd61c10d269273c06cff705a630a9b'
        }
        return self.commands[self.function_name](self.args)

    def get_incident(self, args):
        incident_id = args['Incident-ID']
        url = (settings.VICTOROPS_INCIDENT_ALERT_URL + incident_id)
        response = requests.get(url, headers=self.headers)
        response_json = response.json()
        print(response_json)
        message = MessageClass()
        message.message_text = "Incident Details"

        if bool(response_json) == False:
            attachment = MessageAttachmentsClass()
            attachment.text = "No incident found!"
            message.attach(attachment)
            return message.to_json()
        else:
            attachment = MessageAttachmentsClass()

            field1 = AttachmentFieldsClass()
            field1.title = "Incident Description"
            field1.value = response_json['entityDisplayName']
            attachment.attach_field(field1)

            field2 = AttachmentFieldsClass()
            field2.title = "Incident Body"
            field2.value = response_json['stateMessage']
            attachment.attach_field(field2)

            field3 = AttachmentFieldsClass()
            field3.title = "Entity ID"
            field3.value = response_json['entityId']
            attachment.attach_field(field3)

            field4 = AttachmentFieldsClass()
            field4.title = "Incident Type"
            field4.value = response_json['messageType']
            attachment.attach_field(field4)

            try:
                # val = response_json['ackAuthor']
                field5 = AttachmentFieldsClass()
                field5.title = "Acknowledged By"
                field5.value = response_json['ackAuthor']
                attachment.attach_field(field5)
            except:
                pass

            message.attach(attachment)

            # print(message)
            # message = json.dumps(message)
            # return message
            # print(type(message))
        return message.to_json()

    def list_incidents(self, args):
        print("All incidents")
        api_instance = victorops_client.IncidentsApi()
        x_vo_api_id = settings.VICTOROPS_API_ID  # str | Your API ID
        x_vo_api_key = settings.VICTOROPS_API_KEY  # str | Your API Key

        try:
            # Get current incident information
            api_response = api_instance.incidents_get(x_vo_api_id, x_vo_api_key)
            pprint(api_response)
        except ApiException as e:
            print("Exception when calling IncidentsApi->incidents_get: %s\n" % e)
        response_json = api_response.incidents

        # response_json = response_json.json()
        message = MessageClass()
        message.message_text = "All incidents : "

        if bool(api_response) == False:
            attachment = MessageAttachmentsClass()
            attachment.text = "No incidents"
            message.attach(attachment)
            return message.to_json()
        else:
            # attachment = MessageAttachmentsClass()
            # field1 = AttachmentFieldsClass()
            # field1.title = "User ID :"
            # field1.value = VictorOpsUserToken.victorops_user_id
            # attachment.attach_field(field1)
            for i in range(len(response_json)):
                attachment = MessageAttachmentsClass()

                field2 = AttachmentFieldsClass()
                field2.title = "Incident Number"
                field2.value = response_json[i].incident_number
                # print(field2.value)
                attachment.attach_field(field2)

                field3 = AttachmentFieldsClass()
                field3.title = "Current Phase"
                field3.value = response_json[i].current_phase
                attachment.attach_field(field3)

                field4 = AttachmentFieldsClass()
                field4.title = "Entity ID"
                field4.value = response_json[i].entity_id
                attachment.attach_field(field4)

                field5 = AttachmentFieldsClass()
                field5.title = "VO_UUID"
                field5.value = response_json[i].last_alert_id
                attachment.attach_field(field5)

                message.attach(attachment)

            # print(message)
            # message = json.dumps(message)
            # return message
            # print(type(message))
            return message.to_json()

    def test_list_incidents(self,number):
        api_instance = victorops_client.IncidentsApi()
        x_vo_api_id = settings.VICTOROPS_API_ID  # str | Your API ID
        x_vo_api_key = settings.VICTOROPS_API_KEY  # str | Your API Key

        try:
            # Get current incident information
            api_response = api_instance.incidents_get(x_vo_api_id, x_vo_api_key)
            pprint(api_response)
        except ApiException as e:
            print("Exception when calling IncidentsApi->incidents_get: %s\n" % e)
        response_json = api_response.incidents
        for i in range(len(response_json)):
            if response_json[i].incident_number == number:
                return response_json[i].entity_id, response_json[i].last_alert_id

    def get_user(self, args):
        # create an instance of the API class
        api_instance = victorops_client.UsersApi()
        x_vo_api_id = settings.VICTOROPS_API_ID  # str | Your API ID
        x_vo_api_key = settings.VICTOROPS_API_KEY  # str | Your API Key
        print(args)
        # user = 'adwaithcd'
        user = args['User-ID']  # str | The VictorOps user to fetch

        api_response = []
        try:
            # Retrieve information for a user
            api_response = api_instance.user_user_get(x_vo_api_id, x_vo_api_key, user)
            pprint(api_response)
        except ApiException as e:
            print("Exception when calling UsersApi->user_user_get: %s\n" % e)
        message = MessageClass()
        message.message_text = "User Details"

        if bool(api_response) == False:
            attachment = MessageAttachmentsClass()
            attachment.text = "No user found!"
            message.attach(attachment)
            return message.to_json()
        else:
            attachment = MessageAttachmentsClass()

            field1 = AttachmentFieldsClass()
            field1.title = "Username"
            field1.value = api_response['username']
            attachment.attach_field(field1)

            field2 = AttachmentFieldsClass()
            field2.title = "Name"
            field2.value = str(api_response['firstName']) + " " + str(api_response['lastName'])
            attachment.attach_field(field2)

            field3 = AttachmentFieldsClass()
            field3.title = "Email"
            field3.value = api_response['email']
            attachment.attach_field(field3)

            field4 = AttachmentFieldsClass()
            field4.title = "Password Last Updated"
            field4.value = api_response['passwordLastUpdated']
            attachment.attach_field(field4)

            field5 = AttachmentFieldsClass()
            field5.title = "Verified"
            field5.value = api_response['verified']
            attachment.attach_field(field5)

            message.attach(attachment)

            # print(message)
            # message = json.dumps(message)
            # return message
            # print(type(message))
        return message.to_json()

    def test_get_user(self,user):
        api_instance = victorops_client.UsersApi()
        x_vo_api_id = settings.VICTOROPS_API_ID  # str | Your API ID
        x_vo_api_key = settings.VICTOROPS_API_KEY  # str | Your API Key
        api_response = []
        try:
            # Retrieve information for a user
            api_response = api_instance.user_user_get(x_vo_api_id, x_vo_api_key, user)
            pprint(api_response)
        except ApiException as e:
            print("Exception when calling UsersApi->user_user_get: %s\n" % e)

        if bool(api_response) == False:
            return 0
        else:
            return 1


    def list_users(self, args):
        url = settings.VICTOROPS_ALL_USERS
        response = requests.get(url, headers=self.headers)
        response_json = response.json()
        print(response_json)
        message = MessageClass()
        message.message_text = "Users"
        if bool(response_json) == False:
            attachment = MessageAttachmentsClass()
            attachment.text = "No users!"
            message.attach(attachment)
            return message.to_json()
        else:
            data = response_json['users'][0]
            for i in range(len(data)):
                attachment = MessageAttachmentsClass()

                field1 = AttachmentFieldsClass()
                field1.title = "Username"
                field1.value = data[i]['username']
                attachment.attach_field(field1)

                field2 = AttachmentFieldsClass()
                field2.title = "Name"
                field2.value = str(data[i]['firstName']) + " " + str(data[i]['lastName'])
                attachment.attach_field(field2)

                field3 = AttachmentFieldsClass()
                field3.title = "Email"
                field3.value = data[i]['email']
                attachment.attach_field(field3)

                field4 = AttachmentFieldsClass()
                field4.title = "Password Last Updated"
                field4.value = data[i]['passwordLastUpdated']
                attachment.attach_field(field4)

                field5 = AttachmentFieldsClass()
                field5.title = "Verified"
                field5.value = data[i]['verified']
                attachment.attach_field(field5)

                message.attach(attachment)

                # print(message)
                # message = json.dumps(message)
                # return message
                # print(type(message))
            return message.to_json()

    def create_incident(self, args):
        url = settings.VICTOROPS_CREATE_INCIDENT
        if self.test_get_user(args['Send-To']) == 0:
            message = MessageClass()
            attachment = MessageAttachmentsClass()
            attachment.text = "User not found!"
            message.attach(attachment)
            return message.to_json()
        else:
            body = {
                "summary": args['Incident-Summary'],
                "details": args['Incident-Body'],
                "userName":self.victor_ops_uid,
                "targets": [
                    {
                        "type": "User",
                        "slug": args['Send-To']
                    }
                ]
            }
            r = requests.post(url, headers=self.headers, data=json.dumps(body))
            print(r)
            message = MessageClass()
            attachment = MessageAttachmentsClass()
            attachment.text = "Incident created "
            s = r.text
            a = re.findall('\d+', s)
            print(a[0])
            entity_id , vo_uuid = self.test_list_incidents(a[0])

            field2 = AttachmentFieldsClass()
            field2.title = "Entity ID"
            field2.value = entity_id
            # print(field2.value)
            attachment.attach_field(field2)

            field3 = AttachmentFieldsClass()
            field3.title = "VO_UUID"
            field3.value = vo_uuid
            attachment.attach_field(field3)

            message.attach(attachment)
            return message.to_json()

    def add_user(self,args):
        message = MessageClass()
        url = settings.VICTOROPS_ADD_USER
        body = {
                "firstName": args['First-Name'],
                "lastName": args['Last-Name'],
                "username": args['UserName'],
                "email": args['Email'],
                "admin": True,
                "expirationHours": int(args['Expiration-Hours'])
             }
        r = requests.post(url, headers=self.headers, data=json.dumps(body))
        print(r)
        r = r.text
        print(r)
        if re.search(r'The email address', r, re.M | re.I):
            attachment = MessageAttachmentsClass()
            attachment.text = "The email is already registered"
            message.attach(attachment)
            flag = 0
            return message.to_json(),flag
        elif re.search(r'is unavailable',r,re.M | re.I):
            attachment = MessageAttachmentsClass()
            attachment.text = "Username " +str(args['UserName'])+ " is not available"
            message.attach(attachment)
            flag = 0
            return message.to_json(),flag
        else:
            attachment = MessageAttachmentsClass()
            attachment.text = "User added"
            message.attach(attachment)
            flag = 1
            return message.to_json(),flag

    def ack_incidents(self, args):
        message = MessageClass()
        url = settings.VICTOROPS_ACK_INCIDENTS
        s = args['Incident-Numbers'].split(',')
        body = {
                "userName":self.victor_ops_uid,
                "incidentNames": s,
                "message": args['Acknowledgement-Message']
            }
        r = requests.patch(url, headers=self.headers, data=json.dumps(body))
        print(r)
        # print(type(r))
        print(r.text)
        if re.search(r'Already', r.text, re.M | re.I):
            attachment = MessageAttachmentsClass()
            attachment.text = "The incident is already resolved"
            message.attach(attachment)
            return message.to_json()
        elif re.search(r'User not found', r.text, re.M | re.I):
            attachment = MessageAttachmentsClass()
            attachment.text = "User not found"
            message.attach(attachment)
            return message.to_json()
        else:
            attachment = MessageAttachmentsClass()
            attachment.text = "Acknowledged!"
            message.attach(attachment)
            return message.to_json()

    def resolve_incidents(self, args):
        message = MessageClass()
        url = settings.VICTOROPS_RESOLVE_INCIDENTS
        s = args['Incident-Numbers'].split(',')
        body = {
                "userName":self.victor_ops_uid,
                "incidentNames": s,
                "message": args['Resolution-Message']
            }
        r = requests.patch(url, headers=self.headers, data=json.dumps(body))
        print(r)
        # print(type(r))
        print(r.text)
        if re.search(r'Already', r.text, re.M | re.I):
            attachment = MessageAttachmentsClass()
            attachment.text = "The incident is already resolved"
            message.attach(attachment)
            return message.to_json()
        elif re.search(r'User not found', r.text, re.M | re.I):
            attachment = MessageAttachmentsClass()
            attachment.text = "User not found"
            message.attach(attachment)
            return message.to_json()
        else:
            attachment = MessageAttachmentsClass()
            attachment.text = "Resolved!"
            message.attach(attachment)
            return message.to_json()

    def ack_all_incidents(self,args):
        message = MessageClass()
        url = settings.VICTOROPS_ACK_ALL_INCIDENTS
        body = {
            "userName": self.victor_ops_uid,
            "message": args['Acknowledgement-Message']
        }
        r = requests.patch(url, headers=self.headers, data=json.dumps(body))
        print(r)
        # print(type(r))
        print(r.text)
        if re.search(r'User not found', r.text, re.M | re.I):
            attachment = MessageAttachmentsClass()
            attachment.text = "User not found"
            message.attach(attachment)
            return message.to_json()
        else:
            attachment = MessageAttachmentsClass()
            attachment.text = "Acknowledged all the incidents!"
            message.attach(attachment)
            return message.to_json()

    def resolve_all_incidents(self,args):
        message = MessageClass()
        url = settings.VICTOROPS_RESOLVE_ALL_INCIDENTS
        body = {
            "userName": self.victor_ops_uid,
            "message": args['Resolution-Message']
        }
        r = requests.patch(url, headers=self.headers, data=json.dumps(body))
        print(r)
        # print(type(r))
        print(r.text)
        if re.search(r'User not found', r.text, re.M | re.I):
            attachment = MessageAttachmentsClass()
            attachment.text = "User not found"
            message.attach(attachment)
            return message.to_json()
        else:
            attachment = MessageAttachmentsClass()
            attachment.text = "Resolved all the incidents!"
            message.attach(attachment)
            return message.to_json()









