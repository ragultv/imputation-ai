from flask import Flask, request, jsonify, send_file, render_template, session
import pandas as pd
import os
import random
import string
from datetime import datetime, timedelta
import re
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from twilio.rest import Client
from sklearn.experimental import enable_iterative_imputer  # noqa
from sklearn.impute import IterativeImputer
from sklearn.linear_model import BayesianRidge
from sklearn.impute import KNNImputer

app = Flask(__name__)
app.secret_key = ''.join(random.choices(string.ascii_letters + string.digits, k=32))  # Secret key for sessions

# Directory to save uploaded files
UPLOAD_FOLDER = 'uploads'
IMPUTED_FOLDER = 'imputed'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(IMPUTED_FOLDER, exist_ok=True)

# Configuration for email
EMAIL_SERVER = "smtp.gmail.com"
EMAIL_PORT = 587
EMAIL_ADDRESS = "rwithr2004@gmail.com"  # Replace with your email
EMAIL_PASSWORD = "slta ptzt gmyj ggmp"  # Replace with your app password

# Configuration for Twilio
TWILIO_ACCOUNT_SID = "ACbef0e7f9127fd39c1dc0894977f4e63e"  # Replace with your Twilio SID
TWILIO_AUTH_TOKEN = "710b7c20cbd69fc9ba2620c4e37d5e1a"  # Replace with your Twilio auth token
TWILIO_PHONE_NUMBER = "+14708237104"  # Replace with your Twilio phone number

# Store OTPs temporarily (in production, use a proper database)
otp_store = {}


# Function definitions
def minmax_impute(df):
    """Impute missing numeric values with the midpoint of min and max."""
    numeric_cols = df.select_dtypes(include=['number']).columns
    for col in numeric_cols:
        min_value = df[col].min()
        max_value = df[col].max()
        midpoint = (min_value + max_value) / 2
        df[col].fillna(midpoint, inplace=True)
    return df


def knn_imputation(df, n_neighbors=5):
    """Impute missing values using KNN Imputation with data cleaning."""

    # Convert string representations of lists/arrays to numeric
    def clean_numeric_column(column):
        def parse_value(val):
            try:
                # If it's a string representation of a list, extract first element
                if isinstance(val, str) and val.startswith('[') and val.endswith(']'):
                    val = val.strip('[]').split(',')[0].strip()
                # Convert to float
                return float(val)
            except (ValueError, TypeError):
                return None

        return column.apply(parse_value)

    # Clean numeric columns
    numeric_cols = df.select_dtypes(include=['number', 'object']).columns
    for col in numeric_cols:
        df[col] = clean_numeric_column(df[col])

    # Drop columns with no numeric data
    df = df.dropna(axis=1, how='all')

    # Perform imputation
    imputer = KNNImputer(n_neighbors=n_neighbors)
    imputed_data = imputer.fit_transform(df)

    return pd.DataFrame(imputed_data, columns=df.columns)


def mice_imputation(df):
    """Impute missing values using MICE with data cleaning."""

    # Convert string representations of lists/arrays to numeric
    def clean_numeric_column(column):
        def parse_value(val):
            try:
                # If it's a string representation of a list, extract first element
                if isinstance(val, str) and val.startswith('[') and val.endswith(']'):
                    val = val.strip('[]').split(',')[0].strip()
                # Convert to float
                return float(val)
            except (ValueError, TypeError):
                return None

        return column.apply(parse_value)

    # Clean numeric columns
    numeric_cols = df.select_dtypes(include=['number', 'object']).columns
    for col in numeric_cols:
        df[col] = clean_numeric_column(df[col])

    # Drop columns with no numeric data
    df = df.dropna(axis=1, how='all')

    # Perform imputation
    imputer = IterativeImputer()
    imputed_data = imputer.fit_transform(df)

    return pd.DataFrame(imputed_data, columns=df.columns)

def bayesian_imputation(df):
    """Impute missing values using Bayesian Imputation (simple approach)."""
    # Assume numeric data and use Bayesian Ridge regression for imputation
    for col in df.columns:
        if df[col].isnull().any():
            model = BayesianRidge()
            known_data = df[df[col].notnull()]
            if known_data.empty:
                raise ValueError(f"No known data available for column '{col}' for Bayesian imputation.")
            # Fill any remaining NaNs in known_data
            known_data = known_data.fillna(known_data.mean())
            model.fit(known_data.drop(col, axis=1), known_data[col])
            # Fill any remaining NaNs in data to predict
            predict_data = df[df[col].isnull()].drop(col, axis=1).fillna(df.mean())
            predicted_values = model.predict(predict_data)
            df.loc[df[col].isnull(), col] = predicted_values
    return df
def mean_imputation(df):
    """Impute missing numeric values with the mean."""
    numeric_cols = df.select_dtypes(include=['number']).columns
    for col in numeric_cols:
        mean_value = df[col].mean()  # Calculate mean
        df[col].fillna(mean_value, inplace=True)  # Fill missing values with mean
    return df

def median_imputation(df):
    """Impute missing numeric values with the median."""
    numeric_cols = df.select_dtypes(include=['number']).columns
    for col in numeric_cols:
        median_value = df[col].median()  # Calculate median
        df[col].fillna(median_value, inplace=True)  # Fill missing values with median
    return df

def mode_imputation(df):
    """Impute missing non-numeric values with the mode."""
    non_numeric_cols = df.select_dtypes(exclude=['number']).columns
    for col in non_numeric_cols:
        if df[col].dropna().size > 0:  # Check if there are non-null values to calculate mode
            mode_value = df[col].mode()[0]  # Calculate mode using pandas' mode() function
            df[col].fillna(mode_value, inplace=True)  # Fill missing values with mode
    return df


def forward_fill(df):
    """Fill missing values with the last valid observation."""
    df.fillna(method='ffill', inplace=True)
    return df.round(2)

def backward_fill(df):
    """Fill missing values with the next valid observation."""
    df.fillna(method='bfill', inplace=True)
    return df.round(2)
def generate_otp():
    """Generate a 6-digit OTP"""
    return ''.join(random.choices(string.digits, k=6))


def is_valid_email(email):
    """Validate email format"""
    email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    return bool(email_pattern.match(email))


def is_valid_phone(phone):
    """Validate phone number format"""
    phone_pattern = re.compile(r'^\+?1?\d{9,15}$')
    return bool(phone_pattern.match(phone))


def send_email_otp(email, otp):
    """Send OTP via email"""
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_ADDRESS
        msg['To'] = email
        msg['Subject'] = "Your OTP for Imp AI"

        body = f"We have received a sign-in attempt from your mail.\n \nYour OTP is: {otp}\nValid for 5 minutes."
        msg.attach(MIMEText(body, 'plain'))

        server = smtplib.SMTP(EMAIL_SERVER, EMAIL_PORT)
        server.starttls()
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False


def send_sms_otp(phone_number, otp):
    """Send OTP via SMS using Twilio"""
    try:
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        message = client.messages.create(
            body=f"Your Imp AI OTP is: {otp}. Valid for 5 minutes.",
            from_=TWILIO_PHONE_NUMBER,
            to=phone_number
        )
        return True
    except Exception as e:
        print(f"Error sending SMS: {e}")
        return False


@app.route('/')
def home():
    if 'user_id' not in session:
        return render_template('login.html')
    return render_template('home.html')


@app.route('/login', methods=['POST'])
def login():
    data = request.json
    identifier = data.get('identifier')  # Email or phone number

    if not identifier:
        return jsonify({'error': 'Please provide email or phone number'}), 400

    # Generate OTP
    otp = generate_otp()
    expiry_time = datetime.now() + timedelta(minutes=5)

    # Store OTP with expiry
    otp_store[identifier] = {
        'otp': otp,
        'expiry': expiry_time
    }

    # Send OTP based on identifier type
    if is_valid_email(identifier):
        if send_email_otp(identifier, otp):
            return jsonify({'message': 'OTP sent to email'}), 200
        return jsonify({'error': 'Failed to send OTP email'}), 500

    elif is_valid_phone(identifier):
        if send_sms_otp(identifier, otp):
            return jsonify({'message': 'OTP sent to phone'}), 200
        return jsonify({'error': 'Failed to send OTP SMS'}), 500

    return jsonify({'error': 'Invalid email or phone number format'}), 400

@app.route('/login-otp', methods=['GET'])
def login_otp():
    identifier = request.args.get('identifier')
    if identifier:
        return render_template('login-otp.html', identifier=identifier)
    return jsonify({'error': 'Identifier not provided'}), 400

@app.route('/verify-otp', methods=['POST'])
def verify_otp():
    data = request.json
    identifier = data.get('identifier')
    submitted_otp = data.get('otp')

    if not identifier or not submitted_otp:
        return jsonify({'error': 'Missing identifier or OTP'}), 400

    stored_data = otp_store.get(identifier)
    if not stored_data:
        return jsonify({'error': 'No OTP request found'}), 400

    if datetime.now() > stored_data['expiry']:
        del otp_store[identifier]
        return jsonify({'error': 'OTP expired'}), 400

    if submitted_otp == stored_data['otp']:
        # OTP verified successfully
        session['user_id'] = identifier  # Set session
        del otp_store[identifier]  # Clean up OTP
        return jsonify({'message': 'OTP verified successfully'}), 200

    return jsonify({'error': 'Invalid OTP'}), 400


@app.route('/logout', methods=['POST'])
def logout():
    session.pop('user_id', None)
    return jsonify({'message': 'Logged out successfully'}), 200


@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    filepath = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(filepath)
    return jsonify({'message': 'File uploaded successfully', 'file_name': file.filename}), 200

# Endpoint to handle imputation based on prompt
@app.route('/impute', methods=['POST'])
def impute_data():
    data = request.json
    file_name = data.get('file_name')
    prompt = data.get('prompt')

    # Load the dataset
    df = pd.read_csv(os.path.join(UPLOAD_FOLDER, file_name))

    # Determine which function to use based on prompt
    if "minmax" in prompt.lower():
        imputed_df = minmax_impute(df)
    elif "mode" in prompt.lower():
        imputed_df = mode_imputation(df)
    elif "mean" in prompt.lower():
        imputed_df = mean_imputation(df)
    elif "median" in prompt.lower():
        imputed_df = median_imputation(df)
    elif "forward fill" in prompt.lower():
        imputed_df = forward_fill(df)
    elif "backward fill" in prompt.lower():
        imputed_df = backward_fill(df)
    elif "knn" in prompt.lower():
        imputed_df = knn_imputation(df)
    elif "mice" in prompt.lower():
        imputed_df = mice_imputation(df)
    elif "bayesian" in prompt.lower():
        imputed_df = bayesian_imputation(df)
    else:
        return jsonify({'error': 'please provide the imputation method'}), 400

    # Save the imputed file
    imputed_file_path = os.path.join(IMPUTED_FOLDER, f'imputed_{file_name}')
    imputed_df.to_csv(imputed_file_path, index=False)

    return jsonify({'message': '{prompt}Imputation successful', 'imputed_file_name': f'imputed_{file_name}'}), 200

# Endpoint to download imputed files
@app.route('/download/<filename>', methods=['GET'])
def download_file(filename):
    return send_file(os.path.join(IMPUTED_FOLDER, filename), as_attachment=True)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
