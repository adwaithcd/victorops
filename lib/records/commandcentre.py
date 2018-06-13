""""
    This is the command centre for all the commands created in the YA developer console
    This file contains the logic to understand a user message request from YA
    and return a response in the format of a YA message object accordingly

"""
from __future__ import print_function
import json
from pprint import pprint
import re
import requests
# from yellowant import YellowAnt
from yellowant.messageformat import MessageClass, MessageAttachmentsClass, AttachmentFieldsClass
from django.conf import settings
import victorops_client
from victorops_client.rest import ApiException
from .models import VictorOpsUserToken, YellowUserToken


# The installation documentation for VictorOps API's python package can be found at
# https://github.com/honestbee/python-victorops/tree/master/python-client


class CommandCentre(object):
    """ Handles user commands
        Args:
            yellowant_user_id(int) : The user_id of the user
            yellowant_integration_id (int): The integration id of a YA user
            function_name (str): Invoke name of the command the user is calling
            args (dict): Any arguments required for the command to run
     """

    def __init__(self, yellowant_user_id, yellowant_integration_id, function_name, args):
        self.yellowant_user_id = yellowant_user_id
        self.yellowant_integration_id = yellowant_integration_id
        self.function_name = function_name
        self.args = args

    def parse(self):
        """
            Matching which function to call
        """
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
            'pick_list_users': self.pick_list_users,
        }

        self.user_integration = YellowUserToken.objects.get(yellowant_integration_id=self.yellowant_integration_id)
        self.victor_ops_object = VictorOpsUserToken.objects.get(user_integration=self.user_integration)
        self.victor_ops_uid = self.victor_ops_object.victorops_user_id
        self.victor_ops_api_id = self.victor_ops_object.victorops_api_id
        self.victor_ops_api_key = self.victor_ops_object.victorops_api_key
        self.headers = {
            'Content-Type': 'application/json',
            'X-VO-Api-Id': self.victor_ops_api_id,
            'X-VO-Api-Key': self.victor_ops_api_key
        }
        return self.commands[self.function_name](self.args)

    def get_incident(self, args):
        """
            Get information corresponding to the given incident_uuid
        """
        incident_id = args['Incident-UUID']
        url = (settings.VICTOROPS_INCIDENT_ALERT_URL + incident_id)
        # get request to victorops server
        response = requests.get(url, headers=self.headers)
        # print(response)
        response_json = response.json()
        # print(response_json)
        message = MessageClass()
        message.message_text = "Incident Details"

        # if the ID does not have an incident associated with it.
        if response.status_code == 422:
            attachment = MessageAttachmentsClass()
            attachment.text = "No incident found for the given ID!"
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
        """
            This functions returns the list of the currently open,
             acknowledged and recently resolved incidents.
        """
        # print("All incidents")
        # The request is sent by creating an instance of the victorops_client API and by sending
        # the api key and id to the incidents_get function
        api_instance = victorops_client.IncidentsApi()
        x_vo_api_id = self.victor_ops_api_id  # str | Your API ID
        x_vo_api_key = self.victor_ops_api_key  # str | Your API Key

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

        # Check if there are incidents present
        if not bool(api_response):
            attachment = MessageAttachmentsClass()
            attachment.text = "No incidents"
            message.attach(attachment)
            return message.to_json()
        else:
            for details in response_json:
                attachment = MessageAttachmentsClass()

                field2 = AttachmentFieldsClass()
                field2.title = "Incident Number"
                field2.value = details.incident_number
                # print(field2.value)
                attachment.attach_field(field2)

                field3 = AttachmentFieldsClass()
                field3.title = "Current Phase"
                field3.value = details.current_phase
                attachment.attach_field(field3)

                field4 = AttachmentFieldsClass()
                field4.title = "Entity ID"
                field4.value = details.entity_id
                attachment.attach_field(field4)

                field5 = AttachmentFieldsClass()
                field5.title = "VO_UUID"
                field5.value = details.last_alert_id
                attachment.attach_field(field5)

                message.attach(attachment)

            return message.to_json()

    def test_list_incidents(self, number):
        """
            This function is used to return an incident given the incident number.
            This is a supporting function for create_incident function
        """
        api_instance = victorops_client.IncidentsApi()
        x_vo_api_id = self.victor_ops_api_id  # VictorOps API ID
        x_vo_api_key = self.victor_ops_api_key  # VictorOps API Key

        try:
            # Get current incident information
            api_response = api_instance.incidents_get(x_vo_api_id, x_vo_api_key)
            pprint(api_response)
        except ApiException as e:
            print("Exception when calling IncidentsApi->incidents_get: %s\n" % e)
        response_json = api_response.incidents
        for response in response_json:
            if response.incident_number == number:
                return response.entity_id, response.last_alert_id

    def get_user(self, args):
        """
            This function is used to get the user details given the victorops user id
        """
        # create an instance of the API class
        api_instance = victorops_client.UsersApi()
        x_vo_api_id = self.victor_ops_api_id  # VictorOps API ID
        x_vo_api_key = self.victor_ops_api_key  # VictorOps API Key
        # print(args)
        user = args['User-ID']  # VictorOps user ID

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

        return message.to_json()

    def test_get_user(self, user):
        """
            This function is used to check if the user exists.
            This is a supporting function for create_incident function
        """

        # create an instance of the API class
        api_instance = victorops_client.UsersApi()
        x_vo_api_id = self.victor_ops_api_id  # str | Your API ID
        x_vo_api_key = self.victor_ops_api_key  # str | Your API Key
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

    def pick_list_users(self, args):
        """
            Implements the pick list to list all the users
        """
        url = settings.VICTOROPS_ALL_USERS
        response = requests.get(url, headers=self.headers)
        response_json = response.json()
        message = MessageClass()
        message.message_text = "User List"
        data = response_json['users'][0]
        name_list = {'users': []}
        for i in range(len(data)):
            name_list['users'].append({"username": data[i]['username']})
        print(name_list)
        message.data = name_list
        return message.to_json()

    def list_users(self, args):
        """
            Gives information about the users of the organization
        """
        url = settings.VICTOROPS_ALL_USERS
        response = requests.get(url, headers=self.headers)
        response_json = response.json()
        # print(response_json)
        message = MessageClass()
        message.message_text = "Users"
        if not bool(response_json):
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

            return message.to_json()

    def create_incident(self, args):
        """
            Creates a new incident given the incident body, description
            and the user to be paged for the incident
            A flag is also returned which denotes the success or the failure of incident creation
            which is used to provide a webhook.
        """
        url = settings.VICTOROPS_CREATE_INCIDENT
        # Check if the user to be paged exists
        if self.test_get_user(args['Send-To']) == 0:
            message = MessageClass()
            attachment = MessageAttachmentsClass()
            attachment.text = "User not found!"
            message.attach(attachment)
            flag = 0
            return message.to_json(), flag
        else:
            body = {
                "summary": args['Incident-Summary'],
                "details": args['Incident-Body'],
                "userName": self.victor_ops_uid,
                "targets": [
                    {
                        "type": "User",
                        "slug": args['Send-To']
                    }
                ]
            }
            response = requests.post(url, headers=self.headers, data=json.dumps(body))
            message = MessageClass()
            attachment = MessageAttachmentsClass()
            attachment.text = "Incident created "
            r_text = response.text
            print(r_text)
            # A regex check to find the incident number of the new incident
            incident_nos = re.findall("\d+", r_text)
            # print(incident_nos)
            # print(incident_nos[0])
            entity_id, vo_uuid = self.test_list_incidents(incident_nos[0])

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
            flag = 1
            return message.to_json(), flag

    def add_user(self, args):
        """
            Adds a new user to the organization
        """
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
        # POST request to victorops server
        response = requests.post(url, headers=self.headers, data=json.dumps(body))
        # print(r)
        r_text = response.text
        if re.search(r'The email address', r_text, re.M | re.I):
            attachment = MessageAttachmentsClass()
            attachment.text = "The email is already registered"
            message.attach(attachment)
            flag = 0
            return message.to_json(), flag
        elif re.search(r'is unavailable', r_text, re.M | re.I):
            attachment = MessageAttachmentsClass()
            attachment.text = "Username " + str(args['UserName']) + " is not available"
            message.attach(attachment)
            flag = 0
            return message.to_json(), flag
        else:
            attachment = MessageAttachmentsClass()
            attachment.text = "User added"
            message.attach(attachment)
            flag = 1
            return message.to_json(), flag

    def ack_incidents(self, args):
        """
            This acknowledges an incident or a list of incidents.
        """
        message = MessageClass()
        url = settings.VICTOROPS_ACK_INCIDENTS
        # If there are multiple incidents they are split and added to an array
        incident_list = args['Incident-Numbers'].split(',')
        body = {
            "userName": self.victor_ops_uid,
            "incidentNames": incident_list,
            "message": args['Acknowledgement-Message']
        }
        # PATCH request to victorops server
        response = requests.patch(url, headers=self.headers, data=json.dumps(body))
        r_text = response.text
        if re.search(r'Already', r_text, re.M | re.I):
            attachment = MessageAttachmentsClass()
            attachment.text = "The incident is already resolved"
            message.attach(attachment)
            return message.to_json()
        elif re.search(r'User not found', r_text, re.M | re.I):
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
        """
            This resolves an incident or a list of incidents.
        """
        message = MessageClass()
        url = settings.VICTOROPS_RESOLVE_INCIDENTS
        incident_list = args['Incident-Numbers'].split(',')
        body = {
            "userName": self.victor_ops_uid,
            "incidentNames": incident_list,
            "message": args['Resolution-Message']
        }
        # PATCH request to victorops server
        response = requests.patch(url, headers=self.headers, data=json.dumps(body))
        r_text = response.text
        if re.search(r'Already', r_text, re.M | re.I):
            attachment = MessageAttachmentsClass()
            attachment.text = "The incident is already resolved"
            message.attach(attachment)
            return message.to_json()
        elif re.search(r'User not found', r_text, re.M | re.I):
            attachment = MessageAttachmentsClass()
            attachment.text = "User not found"
            message.attach(attachment)
            return message.to_json()
        else:
            attachment = MessageAttachmentsClass()
            attachment.text = "Resolved!"
            message.attach(attachment)
            return message.to_json()

    def ack_all_incidents(self, args):
        """
            This acknowledges all the incidents the user was paged for.
        """
        message = MessageClass()
        url = settings.VICTOROPS_ACK_ALL_INCIDENTS
        body = {
            "userName": self.victor_ops_uid,
            "message": args['Acknowledgement-Message']
        }
        # PATCH request to victorops server
        response = requests.patch(url, headers=self.headers, data=json.dumps(body))
        r_text = response.text
        if re.search(r'User not found', r_text, re.M | re.I):
            attachment = MessageAttachmentsClass()
            attachment.text = "User not found"
            message.attach(attachment)
            return message.to_json()
        else:
            attachment = MessageAttachmentsClass()
            attachment.text = "Acknowledged all the incidents!"
            message.attach(attachment)
            return message.to_json()

    def resolve_all_incidents(self, args):
        """
            This resolves all the incidents the user was paged for.
        """
        message = MessageClass()
        url = settings.VICTOROPS_RESOLVE_ALL_INCIDENTS
        body = {
            "userName": self.victor_ops_uid,
            "message": args['Resolution-Message']
        }
        # PATCH request to victorops server
        response = requests.patch(url, headers=self.headers, data=json.dumps(body))
        r_text = response.text
        if re.search(r'User not found', r_text, re.M | re.I):
            attachment = MessageAttachmentsClass()
            attachment.text = "User not found"
            message.attach(attachment)
            return message.to_json()
        else:
            attachment = MessageAttachmentsClass()
            attachment.text = "Resolved all the incidents!"
            message.attach(attachment)
            return message.to_json()
