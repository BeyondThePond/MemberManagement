from __future__ import annotations

from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from django.conf import settings
from unittest import mock

from custom_auth.views import email_token_login
from custom_auth.utils.auth import generate_login_token

User = get_user_model()


class EmailTokenLoginRedirectTest(TestCase):
    """Test that email token login respects the 'next' parameter"""
    
    fixtures = ["registry/tests/fixtures/integration.json"]
    
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.get(username="Mounfem")
    
    def test_redirect_with_next_parameter(self):
        """Test that login redirects to the 'next' URL when provided"""
        token = generate_login_token(self.user)
        
        # Create a POST request with a valid token and next parameter
        request = self.factory.post('/auth/magic/', {
            'token': token,
            'next': '/payments/'
        })
        
        with mock.patch('custom_auth.views.authenticate', return_value=self.user):
            with mock.patch('custom_auth.views.login'):
                response = email_token_login(request)
        
        # Should redirect to /payments/
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/payments/')
    
    def test_redirect_without_next_parameter(self):
        """Test that login redirects to LOGIN_REDIRECT_URL when 'next' is not provided"""
        token = generate_login_token(self.user)
        
        # Create a POST request with a valid token but no next parameter
        request = self.factory.post('/auth/magic/', {
            'token': token
        })
        
        with mock.patch('custom_auth.views.authenticate', return_value=self.user):
            with mock.patch('custom_auth.views.login'):
                response = email_token_login(request)
        
        # Should redirect to LOGIN_REDIRECT_URL (default: '/')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, settings.LOGIN_REDIRECT_URL)
    
    def test_redirect_with_empty_next_parameter(self):
        """Test that login redirects to LOGIN_REDIRECT_URL when 'next' is empty"""
        token = generate_login_token(self.user)
        
        # Create a POST request with a valid token and empty next parameter
        request = self.factory.post('/auth/magic/', {
            'token': token,
            'next': ''
        })
        
        with mock.patch('custom_auth.views.authenticate', return_value=self.user):
            with mock.patch('custom_auth.views.login'):
                response = email_token_login(request)
        
        # Should redirect to LOGIN_REDIRECT_URL (default: '/')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, settings.LOGIN_REDIRECT_URL)
    
    def test_redirect_blocks_external_urls(self):
        """Test that external URLs are blocked (security check)"""
        token = generate_login_token(self.user)
        
        # Create a POST request with a valid token and external next URL
        request = self.factory.post('/auth/magic/', {
            'token': token,
            'next': 'https://evil.com/phishing'
        })
        
        with mock.patch('custom_auth.views.authenticate', return_value=self.user):
            with mock.patch('custom_auth.views.login'):
                response = email_token_login(request)
        
        # Should redirect to LOGIN_REDIRECT_URL, not the external URL
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, settings.LOGIN_REDIRECT_URL)
