from flask import Flask, request, jsonify, send_file, render_template, session
import pandas as pd
import os
import random
import string
from datetime import datetime, timedelta
import re
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib
from twilio.rest import Client
from sklearn.experimental import enable_iterative_imputer  # noqa
from sklearn.impute import IterativeImputer
from sklearn.linear_model import BayesianRidge
from sklearn.impute import KNNImputer
import google.generativeai as genai

app = Flask(__name__)
app.secret_key = ''.join(random.choices(string.ascii_letters + string.digits, k=32))  # Secret key for sessions

# Directory to save uploaded files
UPLOAD_FOLDER = 'uploads'
IMPUTED_FOLDER = 'imputed'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(IMPUTED_FOLDER, exist_ok=True)

# Initialize Gemini
GOOGLE_API_KEY = "AIzaSyApppzHOtoyCJm--t3ES6fRruESfs-kH-U"  # Replace with your actual API key
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

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


# Function to retrieve dataset features
def get_dataset_features(df):
    """
    Function to retrieve dataset features, including rows, columns, 
    categorical and numerical data, and the first few rows of the dataset.

    Args:
        dataframe (pd.DataFrame): The dataset as a pandas DataFrame.

    Returns:
        dict: A dictionary containing dataset information.
    """
    dataset_info = {}
    
    # Number of rows and columns
    dataset_info['Number of Rows'] = df.shape[0]
    dataset_info['Number of Columns'] = df.shape[1]

    # size and missing vales 
    dataset_info['Original size'] = f"{len(df)} * {len(df.columns)}"
    dataset_info['missing values'] = df.isnull().sum().sum()
    
    # Categorical and numerical columns
    #categorical_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()
    numerical_cols = df.select_dtypes(include=['int64', 'float64']).columns.tolist()
    #dataset_info['Categorical Columns'] = categorical_cols
    dataset_info['Numerical Columns'] = numerical_cols
    
    # Head of the dataset
    dataset_info['Dataset Head'] = df.head()
    
    return dataset_info

# Function to impute missing values with the midpoint of min and max
def minmax_impute(df):
    """Impute missing numeric values with the midpoint of min and max."""
    numeric_cols = df.select_dtypes(include=['number']).columns
    for col in numeric_cols:
        min_value = df[col].min()
        max_value = df[col].max()
        midpoint = (min_value + max_value) / 2
        df[col].fillna(midpoint, inplace=True)
    return df.round(2)

# Function to impute missing values using KNN Imputation
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

    return pd.DataFrame(imputed_data, columns=df.columns).round(2)

# Function to impute missing values using MICE
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

    return pd.DataFrame(imputed_data, columns=df.columns).round(2)

# Function to impute missing values using Bayesian Ridge regression
def bayesian_imputation(df):
    """Impute missing values using Bayesian Imputation (simple approach)."""
    
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
    return df.round(2)

# Function to impute missing values with the mean
def mean_imputation(df):
    """Impute missing numeric values with the mean."""
    numeric_cols = df.select_dtypes(include=['number']).columns
    for col in numeric_cols:
        mean_value = df[col].mean()  # Calculate mean
        df[col].fillna(mean_value, inplace=True)  # Fill missing values with mean
    return df.round(2)

# Function to impute missing values with the median
def median_imputation(df):
    """Impute missing numeric values with the median."""
    numeric_cols = df.select_dtypes(include=['number']).columns
    for col in numeric_cols:
        median_value = df[col].median()  # Calculate median
        df[col].fillna(median_value, inplace=True)  # Fill missing values with median
    return df.round(2)

# Function to fill missing values with the mode
def mode_imputation(df):
    """Impute missing non-numeric values with the mode."""
    non_numeric_cols = df.select_dtypes(exclude=['number']).columns
    for col in non_numeric_cols:
        if df[col].dropna().size > 0:  # Check if there are non-null values to calculate mode
            mode_value = df[col].mode()[0]  # Calculate mode using pandas' mode() function
            df[col].fillna(mode_value, inplace=True)  # Fill missing values with mode
    return df.round(2)

# Function to fill missing values with the last valid observation
def forward_fill(df):
    """Fill missing values with the last valid observation."""
    df.fillna(method='ffill', inplace=True)
    return df.round(2)

# Function to fill missing values with the next valid observation
def backward_fill(df):
    """Fill missing values with the next valid observation."""
    df.fillna(method='bfill', inplace=True)
    return df.round(2)

#function to generate OTP
def generate_otp():
    """Generate a 6-digit OTP"""
    return ''.join(random.choices(string.digits, k=6))

#function to validate email
def is_valid_email(email):
    """Validate email format"""
    email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    return bool(email_pattern.match(email))

#function to validate phone number
def is_valid_phone(phone):
    """Validate phone number format"""
    phone_pattern = re.compile(r'^\+?1?\d{9,15}$')
    return bool(phone_pattern.match(phone))

#function to send OTP via email
def send_email_otp(email, otp):
    """Send OTP via email with Pinnacle logo"""
    try:
        # Create the email message container
        msg = MIMEMultipart()
        msg['From'] = EMAIL_ADDRESS
        msg['To'] = email
        msg['Subject'] = "OTP for your Imp AI sign-in"

        # HTML body with the Pinnacle logo embedded
        body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; color: #333;">
            <div style="text-align: center;">
                <img src="cid:pinnacle_logo" alt="Pinnacle Logo" style="width: 150px;"/>
            </div>
            <h2 style="color: #1a73e8; text-align: center;">Hi there!</h2>
            <p style="text-align: center;">Use the following one-time password (OTP) to sign in to your Pinnacle account.</p>
            <p style="text-align: center;">This OTP will be valid for <strong>5 minutes</strong>:</p>
            <h1 style="color: #333; font-size: 24px; text-align: center;">{otp}</h1>
            <p style="text-align: center;">If you did not request this OTP, please ignore this email.</p>
            <br>
            <p style="text-align: center;">Regards,<br>The Pinnacle Team</p>
        </body>
        </html>
        """

        msg.attach(MIMEText(body, 'html'))

        # Attach the Pinnacle logo as an image
        with open('pinnacle.jpg', 'rb') as img_file:
            img = MIMEImage(img_file.read())
            img.add_header('Content-ID', '<pinnacle_logo>')
            msg.attach(img)

        # Sending email
        server = smtplib.SMTP(EMAIL_SERVER, EMAIL_PORT)
        server.starttls()
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()

        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False

#function to send OTP via SMS
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

#function to get response from Gemini AI
def get_gemini_response(prompt="", context=None):
    """Get response from Gemini AI"""
    try:
        if context:
            full_prompt = f"{context}\n{prompt}"
        else:
            full_prompt = prompt

        response = model.generate_content(full_prompt)
        return response.text
    except Exception as e:
        return f"I apologize, but I encountered an error: {str(e)}"

#enpoint to render home page
@app.route('/')
def home():
    if 'user_id' not in session:
        return render_template('index.html')
    return render_template('home.html')

#endpoint to render login page
@app.route('/login', methods=['GET'])
def login_page():
    return render_template('login.html')

#endpoint to handle login
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

#endpoint to resend OTP
@app.route('/resend-otp', methods=['POST'])
def resend_otp():
    data = request.json
    identifier = data.get('identifier')  # Email or phone number

    if not identifier:
        return jsonify({'error': 'Please provide email or phone number'}), 400

    # Check if identifier exists in the OTP store
    if identifier not in otp_store:
        return jsonify({'error': 'No OTP request found for this identifier'}), 404

    # Generate new OTP
    otp = generate_otp()
    expiry_time = datetime.now() + timedelta(minutes=5)

    # Update OTP store with new OTP and expiry time
    otp_store[identifier] = {
        'otp': otp,
        'expiry': expiry_time
    }

    # Resend OTP based on identifier type
    if is_valid_email(identifier):
        if send_email_otp(identifier, otp):
            return jsonify({'message': 'OTP resent to email'}), 200
        return jsonify({'error': 'Failed to resend OTP email'}), 500

    elif is_valid_phone(identifier):
        if send_sms_otp(identifier, otp):
            return jsonify({'message': 'OTP resent to phone'}), 200
        return jsonify({'error': 'Failed to resend OTP SMS'}), 500

    return jsonify({'error': 'Invalid email or phone number format'}), 400

#endpoint to render OTP verification page
@app.route('/login-otp', methods=['GET'])
def login_otp():
    identifier = request.args.get('identifier')
    if identifier:
        return render_template('login-otp.html', identifier=identifier)
    return jsonify({'error': 'Identifier not provided'}), 400

#endpoint to verify OTP
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

#endpoint to logout
@app.route('/logout', methods=['POST'])
def logout():
    session.pop('user_id', None)
    return jsonify({'message': 'Logged out successfully'}), 200

#endpoint to handle chat messages
@app.route('/chat', methods=['POST'])
def chat():
    """Handle chat messages"""
    data = request.json
    message = data.get('message', '')

    if not message:
        return jsonify({'error': 'No message provided'}), 400

    # Initial greeting
    if any(greeting in message.lower() for greeting in ['hi', 'hello', 'hey']):
        response = "Hello! I'm your AI assistant for data imputation. You can Upload your CSV file. Tell me which imputation method you'd like to use. I'll help you analyze the results!"
        return jsonify({'response': response}), 200

    return jsonify({'response': get_gemini_response(message)}), 200


#endpoint to upload the dataset
@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    filepath = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(filepath)

    try:
        df = pd.read_csv(filepath)
        features = get_dataset_features(df)
        context = f"The dataset has the following features: {features}"
        
        ai_response = get_gemini_response(
            """
             1.Use <p> tags for paragraphs.
             2.only suggest the  one best imputation method.
             3.only return the method name in uppercase with bold, without any additional text or explanation.
        
            """,
            context
        )
        formatted_response = f"""
        <div class='ai-response'>
            {ai_response}
        </div>
        """
    
        return jsonify({
            'message': 'File uploaded successfully',
            'file_name': file.filename,
            'ai_suggestion': formatted_response
        }), 200
    except Exception as e:
        return jsonify({'error': f"An error occurred: {e}"}), 500


# Endpoint to handle imputation based on prompt

@app.route('/impute', methods=['POST'])
def impute_data():
    data = request.json
    file_name = data.get('file_name')
    prompt = data.get('prompt')

    if not file_name or not prompt:
        return jsonify({'error': 'Missing file name or prompt'}), 400

    try:
        # Load the dataset
        df = pd.read_csv(os.path.join(UPLOAD_FOLDER, file_name))
        
        # Get dataset features for context
        features = get_dataset_features(df)
        
        # Ask Gemini to analyze the prompt and suggest imputation method
        analysis_prompt = f"""
        Based on the following information, determine the most appropriate imputation method:
        
        User prompt: {prompt}
        Dataset features: {features}
        
        Choose one of these methods: minmax, mode, mean, median, forward fill, backward fill, knn, mice, bayesian
        
        Return only the method name in lowercase, without any additional text or explanation.
        """
        
        method = get_gemini_response(analysis_prompt).strip().lower()

        # Map methods to functions
        imputation_methods = {
            'minmax': (minmax_impute, "Min-Max"),
            'mode': (mode_imputation, "Mode"),
            'mean': (mean_imputation, "Mean"),
            'median': (median_imputation, "Median"),
            'forward fill': (forward_fill, "Forward Fill"),
            'backward fill': (backward_fill, "Backward Fill"),
            'knn': (knn_imputation, "KNN"),
            'mice': (mice_imputation, "MICE"),
            'bayesian': (bayesian_imputation, "Bayesian")
        }

        if method not in imputation_methods:
            return jsonify({'error': 'Invalid imputation method suggested'}), 400

        # Apply the chosen imputation method
        impute_func, method_used = imputation_methods[method]
        imputed_df = impute_func(df)

        # Save the imputed file
        imputed_file_name = f'imputed_{file_name}'
        imputed_file_path = os.path.join(IMPUTED_FOLDER, imputed_file_name)
        imputed_df.to_csv(imputed_file_path, index=False)

        # Generate AI response about the imputation
        context = f"""
        Imputation Method: {method_used}
        File Name: {file_name}
        Original Dataset Features: {features}
        User's Original Request: {prompt}
        """

        ai_response = get_gemini_response(
            """
            Generate a structured response with the following format:
            1. Use <h2> tags for main headings
            2. Use <h3> tags for subheadings
            3. Use <p> tags for paragraphs
            4. Use <ul> and <li> tags for bullet points
            5. Include the following sections:
               - Method Selection
               - Implementation Details
               - Benefits and Advantages
               - Results Summary
            Make the response visually organized and easy to read.
            """,
            context
        )


                # Format the response with HTML
        formatted_response = f"""
        <div class='ai-response'>
            {ai_response}
        </div>
        """

        return jsonify({
            'message': 'Imputation successful',
            'imputed_file_name': imputed_file_name,
            'method_used': method_used,
            'ai_response': formatted_response
        }), 200

    except Exception as e:
        return jsonify({'error': f'Error during imputation: {str(e)}'}), 500


# Endpoint to download imputed files
@app.route('/download/<filename>', methods=['GET'])
def download_file(filename):
    return send_file(os.path.join(IMPUTED_FOLDER, filename), as_attachment=True)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)

    