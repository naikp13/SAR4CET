#!/bin/bash

# Copernicus Dataspace Account Troubleshooting Script
# Based on official documentation: https://documentation.dataspace.copernicus.eu/

echo "=== Copernicus Dataspace Account Troubleshooting ==="
echo "Timestamp: $(date)"
echo ""

# Check if credentials are set
if [ -z "$COPERNICUS_USER" ] || [ -z "$COPERNICUS_PASSWORD" ]; then
    echo "❌ ERROR: Environment variables not set"
    echo "Please run:"
    echo "export COPERNICUS_USER='naik15@umd.edu'"
    echo "export COPERNICUS_PASSWORD='Naik@2024'"
    exit 1
fi

echo "✓ Username: $COPERNICUS_USER"
echo "✓ Password: $(echo $COPERNICUS_PASSWORD | sed 's/./*/g')"
echo ""

echo "🔍 Testing OAuth2 Authentication..."
echo "-----------------------------------"

# Test authentication
RESPONSE=$(curl -s -X POST https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d "username=${COPERNICUS_USER}" \
    -d "password=${COPERNICUS_PASSWORD}" \
    -d "grant_type=password" \
    -d "client_id=cdse-public")

echo "Raw API Response:"
echo "$RESPONSE"
echo ""

# Check if we got a token
if echo "$RESPONSE" | grep -q '"access_token"'; then
    echo "✅ SUCCESS: Authentication successful!"
    echo "Your account is working properly."
    
    # Extract and test the token
    ACCESS_TOKEN=$(echo "$RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('access_token', ''))" 2>/dev/null)
    
    if [ -n "$ACCESS_TOKEN" ]; then
        echo "🔍 Testing API access with token..."
        API_RESPONSE=$(curl -s -H "Authorization: Bearer $ACCESS_TOKEN" \
            "https://catalogue.dataspace.copernicus.eu/odata/v1/Products?\$top=1")
        
        if echo "$API_RESPONSE" | grep -q '"@odata.count"'; then
            echo "✅ SUCCESS: API access working!"
            echo "Your account is fully functional."
        else
            echo "⚠️  WARNING: Token obtained but API access failed"
            echo "API Response: $API_RESPONSE"
        fi
    fi
else
    echo "❌ FAILED: Authentication failed"
    
    # Parse error details
    if echo "$RESPONSE" | grep -q '"error"'; then
        ERROR=$(echo "$RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('error', 'Unknown'))" 2>/dev/null)
        ERROR_DESC=$(echo "$RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('error_description', 'Unknown'))" 2>/dev/null)
        
        echo "Error: $ERROR"
        echo "Description: $ERROR_DESC"
        
        if [ "$ERROR_DESC" = "Invalid user credentials" ]; then
            echo ""
            echo "🚨 ACCOUNT ISSUE DETECTED: Invalid user credentials"
            echo "This typically indicates one of the following:"
            echo ""
            echo "1. ❌ EMAIL NOT VERIFIED"
            echo "   - Check your email inbox for a verification email from Copernicus"
            echo "   - Look in spam/junk folders too"
            echo "   - Click the verification link in the email"
            echo ""
            echo "2. ❌ TERMS & CONDITIONS NOT ACCEPTED"
            echo "   - Log into https://dataspace.copernicus.eu/"
            echo "   - Accept all Terms & Conditions and Privacy Policy"
            echo "   - Complete your profile if prompted"
            echo ""
            echo "3. ❌ ACCOUNT NOT FULLY ACTIVATED"
            echo "   - New accounts may take up to 24 hours to activate"
            echo "   - Wait and try again later"
            echo ""
            echo "4. ❌ INCORRECT PASSWORD"
            echo "   - Try resetting your password on the website"
            echo "   - Ensure no special characters are causing issues"
            echo ""
            echo "5. ❌ ACCOUNT SUSPENDED OR RESTRICTED"
            echo "   - Contact help-login@dataspace.copernicus.eu"
            echo ""
        fi
    fi
fi

echo ""
echo "📋 IMMEDIATE ACTION ITEMS:"
echo "1. 🌐 Go to https://dataspace.copernicus.eu/"
echo "2. 🔑 Try logging in with your credentials"
echo "3. ✅ If login works, check for any pending verifications"
echo "4. 📜 Accept any outstanding Terms & Conditions"
echo "5. 📧 Check email for verification messages"
echo "6. ⏰ If recently registered, wait 24 hours"
echo "7. 🆘 If all else fails, contact help-login@dataspace.copernicus.eu"
echo ""
echo "📞 SUPPORT CONTACT:"
echo "Email: help-login@dataspace.copernicus.eu"
echo "Include this error message and your username in your support request."