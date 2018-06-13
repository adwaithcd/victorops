"""

VictorOps application models defined here.

"""
import datetime
from django.db import models
from django.contrib.auth.models import User


class YellowUserToken(models.Model):
    """
        Parent table for the database(contains the primary key).
    """
    user = models.IntegerField()
    yellowant_token = models.CharField(max_length=100)
    yellowant_id = models.IntegerField(default=0)
    yellowant_integration_invoke_name = models.CharField(max_length=100)
    yellowant_integration_id = models.IntegerField(default=0)
    webhook_id = models.CharField(max_length=100, default="")
    webhook_last_updated = models.DateTimeField(default=datetime.datetime.utcnow)


class YellowAntRedirectState(models.Model):
    """
        Child table
    """
    user = models.IntegerField()
    state = models.CharField(max_length=512, null=False)


class AppRedirectState(models.Model):
    """
        Child table
    """
    user_integration = models.ForeignKey(YellowUserToken, on_delete=models.CASCADE)
    state = models.CharField(max_length=512, null=False)


class VictorOpsUserToken(models.Model):
    """
        VictorOpsUserToken stores the user_id, API ID, API Key
        and a flag to identify if the details are present.
    """
    user_integration = models.ForeignKey(YellowUserToken, on_delete=models.CASCADE)
    victorops_user_id = models.TextField(max_length=200)
    victorops_api_id = models.TextField(max_length=200)
    victorops_api_key = models.TextField(max_length=200)
    apikey_login_update_flag = models.BooleanField(default=False, max_length=100)
