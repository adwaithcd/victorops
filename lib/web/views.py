"""
Functions corresponding to URL patterns of web app

"""
import json
import requests
from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import render
from yellowant import YellowAnt
from ..records.models import YellowUserToken, VictorOpsUserToken


def index(request, path):
    """
        Loads the homepage of the app.
        index function loads the home.html page
    """
    # print('test')

    context = {
        "base_href": settings.BASE_HREF,
        "application_id": settings.YELLOWANT_APP_ID,
        "user_integrations": []
    }
    # Check if user is authenticated otherwise redirect user to login page
    if request.user.is_authenticated:
        user_integrations = YellowUserToken.objects.filter(user=request.user.id)
        # print(user_integrations)
        # for user_integration in user_integrations:
        #     context["user_integrations"].append(user_integration)
    return render(request, "home.html", context)


def userdetails(request):
    """
        userdetails function shows the vital integration details of the user
    """
    # print("in userdetails")
    user_integrations_list = []
    # Returns the integration id,user_invoke_name for an integration
    if request.user.is_authenticated:
        user_integrations = YellowUserToken.objects.filter(user=request.user.id)
        # print(user_integrations)
        for user_integration in user_integrations:
            try:
                vout = VictorOpsUserToken.objects.get(user_integration=user_integration)
                # print(vout)
                user_integrations_list.append({"user_invoke_name": user_integration.\
                                              yellowant_integration_invoke_name,
                                               "id": user_integration.id, "app_authenticated": True,
                                               "is_valid": vout.apikey_login_update_flag})
            except VictorOpsUserToken.DoesNotExist:
                user_integrations_list.append({"user_invoke_name": user_integration.\
                                              yellowant_integration_invoke_name,
                                               "id": user_integration.id,
                                               "app_authenticated": False})
    return HttpResponse(json.dumps(user_integrations_list), content_type="application/json")


def user_detail_update_delete_view(request, id=None):
    """
        This function handles the updating, deleting and viewing user details
    """
    # print("In user_detail_update_delete_view")
    # print(id)
    user_integration_id = id
    if request.method == "GET":
        # return user data
        vout = VictorOpsUserToken.objects.get(user_integration=user_integration_id)
        return HttpResponse(json.dumps({
            "is_valid": vout.apikey_login_update_flag
        }))

    elif request.method == "DELETE":
        # deletes the integration
        access_token_dict = YellowUserToken.objects.get(id=id)
        user_id = access_token_dict.user
        if user_id == request.user.id:
            access_token = access_token_dict.yellowant_token
            user_integration_id = access_token_dict.yellowant_integration_id
            url = "https://api.yellowant.com/api/user/integration/%s" % (user_integration_id)
            yellowant_user = YellowAnt(access_token=access_token)
            yellowant_user.delete_user_integration(id=user_integration_id)
            response_json = YellowUserToken.objects.get(yellowant_token=access_token).delete()
            # print(response_json)
            return HttpResponse("successResponse", status=204)
        else:
            return HttpResponse("Not Authenticated", status=403)
    elif request.method == "PUT":
        # adds a new integration
        data = json.loads(request.body.decode("utf-8"))
        # print(data)
        user_id = data['user_id']
        api_id = data['victorops_api_id']
        api_key = data['victorops_api_key']
        user_integration = data['user_integration']

        headers = {
            'Content-Type': 'application/json', 'X-VO-Api-Id': api_id,
            'X-VO-Api-Key': api_key}

        url = 'https://api.victorops.com/api-public/v1/user'
        response = requests.get(url, headers=headers)
        response_json = response.json()
        data = response_json['users'][0]
        response.status_code = 401
        for i in range(len(data)):
            if data[i]['username'] == user_id:
                response.status_code = 200

        if response.status_code == 200:
            # print("Valid")
            api_new = VictorOpsUserToken.objects.get(user_integration_id=user_integration)
            api_new.victorops_user_id = user_id
            api_new.victorops_api_id = api_id
            api_new.victorops_api_key = api_key
            api_new.apikey_login_update_flag = True
            api_new.save()
            return HttpResponse("Submitted", status=200)
        else:
            # print("Invalid")
            return HttpResponse("Invalid Credentials", status=401)
