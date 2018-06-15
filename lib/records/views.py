""" This file contains all functions corresponding to their urls"""

import json
import uuid
import traceback
from django.http import HttpResponseRedirect, HttpResponse
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.models import User
from django.views.decorators.http import require_POST
from yellowant import YellowAnt
from yellowant.messageformat import MessageClass, MessageAttachmentsClass, \
    MessageButtonsClass, AttachmentFieldsClass
from .models import YellowUserToken, YellowAntRedirectState, \
    AppRedirectState, VictorOpsUserToken
from .commandcentre import CommandCentre


def redirectToYellowAntAuthenticationPage(request):

    """Initiate the creation of a new user integration on YA
       YA uses oauth2 as its authorization framework.
       This method requests for an oauth2 code from YA to start creating a
       new user integration for this application on YA.
    """
    # Generate a unique ID to identify the user when YA returns an oauth2 code
    user = User.objects.get(id=request.user.id)
    state = str(uuid.uuid4())

    # Save the relation between user and state so that we can identify the user
    # when YA returns the oauth2 code
    YellowAntRedirectState.objects.create(user=user.id, state=state)

    # Redirect the application user to the YA authentication page.
    # Note that we are passing state, this app's client id,
    # oauth response type as code, and the url to return the oauth2 code at.
    return HttpResponseRedirect("{}?state={}&client_id={}&response_type=code&redirect_url={}".format
                                (settings.YELLOWANT_OAUTH_URL, state, settings.YELLOWANT_CLIENT_ID,
                                 settings.YELLOWANT_REDIRECT_URL))


def yellowantRedirecturl(request):

    """ Receive the oauth2 code from YA to generate a new user integration
            This method calls utilizes the YA Python SDK to create a new user integration on YA.
            This method only provides the code for creating a new user integration on YA.
            Beyond that, you might need to authenticate the user on
            the actual application (whose APIs this application will be calling)
            and store a relation between these user auth details and the YA user integration.
    """
    # Oauth2 code from YA, passed as GET params in the url
    code = request.GET.get('code')

    # The unique string to identify the user for which we will create an integration
    state = request.GET.get("state")

    # Fetch user with help of state from database
    yellowant_redirect_state = YellowAntRedirectState.objects.get(state=state)
    user = yellowant_redirect_state.user

    # Initialize the YA SDK client with your application credentials
    y = YellowAnt(app_key=settings.YELLOWANT_CLIENT_ID,
                  app_secret=settings.YELLOWANT_CLIENT_SECRET, access_token=None,
                  redirect_uri=settings.YELLOWANT_REDIRECT_URL)

    # Getting the acccess token
    access_token_dict = y.get_access_token(code)
    access_token = access_token_dict["access_token"]

    # Getting YA user details
    yellowant_user = YellowAnt(access_token=access_token)
    profile = yellowant_user.get_user_profile()

    # Creating a new user integration for the application
    user_integration = yellowant_user.create_user_integration()
    hash_str = str(uuid.uuid4()).replace("-", "")[:25]
    ut = YellowUserToken.objects.create(user=user, yellowant_token=access_token,
                                        yellowant_id=profile['id'],
                                        yellowant_integration_invoke_name=user_integration \
                                        ["user_invoke_name"],
                                        yellowant_integration_id=user_integration\
                                        ['user_application'],
                                        webhook_id=hash_str)
    state = str(uuid.uuid4())
    AppRedirectState.objects.create(user_integration=ut, state=state)
    VictorOpsUserToken.objects.create(user_integration=ut, victorops_user_id="",
                                      victorops_api_id="", victorops_api_key="")
    web_url = settings.BASE_URL + "/webhook/" + hash_str + "/"
    print(web_url)
    # Redirecting to home page
    return HttpResponseRedirect("/")


@csrf_exempt
def incident_triggered(request, webhook_id):

    """
        Webhook function to notify user about newly created incident
    """
    # Extracting necessary data
    data = request.body
    data_string = data.decode('utf-8')
    data_json = json.loads(data_string)

    name = data_json['display_name']
    entity_id = data_json['entity_id']
    incident_number = data_json['incident_number']
    # Fetching yellowant object
    yellow_obj = YellowUserToken.objects.get(webhook_id=webhook_id)
    access_token = yellow_obj.yellowant_token
    integration_id = yellow_obj.yellowant_integration_id
    service_application = str(integration_id)

    # Creating message object for webhook message
    webhook_message = MessageClass()
    webhook_message.message_text = "Incident Triggered\n The entity ID : " + str(entity_id)\
                                   + "\nThe Incident Number : " + str(incident_number) +\
                                   "\n Incident message : " + str(name)
    attachment = MessageAttachmentsClass()
    attachment.title = "Incident Operations"

    # button_get_incidents = MessageButtonsClass()
    # button_get_incidents.name = "1"
    # button_get_incidents.value = "1"
    # button_get_incidents.text = "Get all incidents"
    # button_get_incidents.command = {
    #     "service_application": service_application,
    #     "function_name": 'list_incidents',
    #     "data": {
    #         'data': "test",
    #     }
    # }
    #
    # attachment.attach_button(button_get_incidents)

    button_ack_incidents = MessageButtonsClass()
    button_ack_incidents.name = "2"
    button_ack_incidents.value = "2"
    button_ack_incidents.text = "Acknowledge the current incident"
    button_ack_incidents.command = {
        "service_application": service_application,
        "function_name": 'ack_incidents',
        "data": {
            "Incident-Numbers": incident_number,
        },
        "inputs": ["Acknowledgement-Message"]
    }

    attachment.attach_button(button_ack_incidents)

    webhook_message.attach(attachment)
    # print(integration_id)
    webhook_message.data = {
        "Display Name": name,
        "Entity ID": entity_id,
        "Incident Number": incident_number,
    }

    # Creating yellowant object
    yellowant_user_integration_object = YellowAnt(access_token=access_token)

    # Sending webhook message to user
    yellowant_user_integration_object.create_webhook_message(
        requester_application=integration_id,
        webhook_name="new_incident", **webhook_message.get_dict())

    return HttpResponse("OK", status=200)


@csrf_exempt
def incident_acknowledge(request, webhook_id):
    """
        Webhook function to notify user about newly added user
    """

    data = request.body
    data_string = data.decode('utf-8')
    data_json = json.loads(data_string)

    name = data_json['display_name']
    entity_id = data_json['entity_id']
    incident_number = data_json['incident_number']
    # Fetching yellowant object
    yellow_obj = YellowUserToken.objects.get(webhook_id=webhook_id)
    access_token = yellow_obj.yellowant_token
    integration_id = yellow_obj.yellowant_integration_id
    service_application = str(integration_id)

    # Creating message object for webhook message
    webhook_message = MessageClass()
    webhook_message.message_text = "Incident Acknowledged\n The entity ID : " + str(entity_id) \
                                   + "\nThe Incident Number : " + str(incident_number)
    attachment = MessageAttachmentsClass()
    attachment.title = "Incident Operations"

    # button_get_incidents = MessageButtonsClass()
    # button_get_incidents.name = "1"
    # button_get_incidents.value = "1"
    # button_get_incidents.text = "Get all incidents"
    # button_get_incidents.command = {
    #     "service_application": service_application,
    #     "function_name": 'list_incidents',
    #     "data": {
    #         'data': "test",
    #     }
    # }
    #
    # attachment.attach_button(button_get_incidents)

    button_ack_incidents = MessageButtonsClass()
    button_ack_incidents.name = "2"
    button_ack_incidents.value = "2"
    button_ack_incidents.text = "Resolve the current incident"
    button_ack_incidents.command = {
        "service_application": service_application,
        "function_name": 'resolve_incidents',
        "data": {
            "Incident-Numbers": incident_number,
        },
        "inputs": ["Resolution-Message"]
    }

    attachment.attach_button(button_ack_incidents)

    webhook_message.attach(attachment)
    # print(integration_id)
    webhook_message.data = {
        "Display Name": name,
        "Entity ID": entity_id,
        "Incident Number": incident_number,
    }

    # Creating yellowant object
    yellowant_user_integration_object = YellowAnt(access_token=access_token)

    # Sending webhook message to user
    yellowant_user_integration_object.create_webhook_message(
        requester_application=integration_id,
        webhook_name="new_incident_acknowledged", **webhook_message.get_dict())

    return HttpResponse("OK", status=200)


@csrf_exempt
def incident_resolved(request, webhook_id):
    #
    data = request.body
    data_string = data.decode('utf-8')
    data_json = json.loads(data_string)

    name = data_json['display_name']
    entity_id = data_json['entity_id']
    incident_number = data_json['incident_number']
    # Fetching yellowant object
    yellow_obj = YellowUserToken.objects.get(webhook_id=webhook_id)
    access_token = yellow_obj.yellowant_token
    integration_id = yellow_obj.yellowant_integration_id
    service_application = str(integration_id)

    # Creating message object for webhook message
    webhook_message = MessageClass()
    webhook_message.message_text = "Incident Resolved\n The entity ID : " + str(entity_id) \
                                   + "\nThe Incident Number : " + str(incident_number)
    attachment = MessageAttachmentsClass()
    attachment.title = "Incident Operations"

    button_get_incidents = MessageButtonsClass()
    button_get_incidents.name = "1"
    button_get_incidents.value = "1"
    button_get_incidents.text = "Get all incidents"
    button_get_incidents.command = {
        "service_application": service_application,
        "function_name": 'list_incidents',
        "data": {
            'data': "test",
        }
    }

    attachment.attach_button(button_get_incidents)
    webhook_message.attach(attachment)
    # print(integration_id)
    webhook_message.data = {
        "Display Name": name,
        "Entity ID": entity_id,
        "Incident Number": incident_number,
    }

    # Creating yellowant object
    yellowant_user_integration_object = YellowAnt(access_token=access_token)

    # Sending webhook message to user
    yellowant_user_integration_object.create_webhook_message(
        requester_application=integration_id,
        webhook_name="new_incident_resolved", **webhook_message.get_dict())

    return HttpResponse("OK", status=200)


@csrf_exempt
@require_POST
def webhook(request, hash_str=""):
    """
    {" display_name":"${{ALERT.entity_display_name}}","message_type":"${{ALERT.message_type}}",
    "alert_count": "${{STATE.ALERT_COUNT}}","alert_phase": "${{STATE.CURRENT_ALERT_PHASE}}",
    "entity_id": "${{STATE.ENTITY_ID}}","incident_number": "${{STATE.INCIDENT_NAME}}",
    "message":  "${{STATE.SERVICE}}" } --> This is the webhook format
    """
    # print("Inside webhook")
    data = request.body
    data_string = data.decode('utf-8')
    data_json = json.loads(data_string)

    if(data_json["alert_count"]) == '1':
        # print("in pipeline webhook")
        incident_triggered(request, hash_str)

    elif(data_json["alert_count"]) == '2':
        # print("in user webhook")
        incident_acknowledge(request, hash_str)

    elif(data_json["alert_count"]) == '3':
        # print("in deal webhook")
        incident_resolved(request, hash_str)

    return HttpResponse("OK", status=200)


@csrf_exempt
def yellowantapi(request):
    """
        Receive user commands from YA
    """
    try:

        # Extracting the necessary data
        data = json.loads(request.POST['data'])
        args = data["args"]
        service_application = data["application"]
        verification_token = data['verification_token']
        # function_id = data['function']
        function_name = data['function_name']
        # print(data)

        # Verifying whether the request is actually from YA using verification token
        if verification_token == settings.YELLOWANT_VERIFICATION_TOKEN:

            # Processing command in some class Command and sending a Message Object
            # Add_user and create_incident have flags to identify the status of the operation
            # and send webhook only if the operation is successful

            message = CommandCentre(data["user"], service_application, function_name, args).parse()
            return HttpResponse(message)
        else:
            # Handling incorrect verification token
            error_message = {"message_text": "Incorrect Verification token"}
            return HttpResponse(json.dumps(error_message), content_type="application/json")
    except Exception as e:
        # Handling exception
        print(str(e))
        traceback.print_exc()
        return HttpResponse("Something went wrong")
