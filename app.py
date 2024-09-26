from flask import Flask, request, render_template, redirect, url_for, flash, session
import boto3
import os
import json
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['SECRET_KEY'] = 'RtVgll3WoJtu2nDzr3t1yaP58xRI5ylsdX4n/syI'
app.config['UPLOAD_FOLDER'] = '/tmp/'

# AWS configurations
S3_BUCKET = 'achinta3-cloudproject'
LAMBDA_FUNCTION_NAME = 'cloudproject-function'
LAMBDA_REGION = 'us-east-1'

dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
users_table = dynamodb.Table('users_table')  # Ensure this table is created in DynamoDB
s3 = boto3.client('s3', region_name='us-west-1')
lambda_client = boto3.client('lambda', region_name=LAMBDA_REGION)

@app.route('/')
def index():
    if 'user_email' not in session:
        return redirect(url_for('login'))
    return render_template('upload.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        response = users_table.get_item(Key={'email': email})
        user = response.get('Item')
        if user and user['password'] == password:
            session['user_email'] = email
            return redirect(url_for('index'))
        flash('Invalid email or password')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        users_table.put_item(Item={'email': email, 'password': password})
        flash('Registration successful, please log in')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/logout', methods=['GET', 'POST'])
def logout():
    session.pop('user_email', None)
    return redirect(url_for('login'))

@app.route('/upload', methods=['POST'])
def upload():
    if 'user_email' not in session:
        return redirect(url_for('login'))

    if 'file' not in request.files:
        flash('No file part')
        return redirect(request.url)
    
    file = request.files['file']
    if file.filename == '':
        flash('No selected file')
        return redirect(request.url)
    
    if file:
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # Upload to S3
        s3.upload_file(filepath, S3_BUCKET, filename)
        
        # Get emails
        emails = request.form.get('emails').split(',')
        
        # Prepare payload for Lambda function
        payload = {
            'filename': filename,
            'emails': emails,
            'uploaded_by': session['user_email']
        }
 
        try:
            response = lambda_client.invoke(
                FunctionName=LAMBDA_FUNCTION_NAME,
                InvocationType='RequestResponse',
                Payload=json.dumps(payload)
            )
            response_payload = json.loads(response['Payload'].read())
            if response_payload['statusCode'] == 200:
                flash('File uploaded and emails sent successfully')
            else:
                flash(f"Error: {response_payload['body']}")
        except Exception as e:
            flash(f"Error invoking Lambda function: {str(e)}")
        
        return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)


# from flask import Flask, request, render_template, redirect, url_for, flash
# import boto3
# import os
# import json
# from werkzeug.utils import secure_filename

# app = Flask(__name__)
# app.config['SECRET_KEY'] = 'RtVgll3WoJtu2nDzr3t1yaP58xRI5ylsdX4n/syI'
# app.config['UPLOAD_FOLDER'] = '/tmp/'

# # AWS configurations
# S3_BUCKET = 'achinta3-cloudproject'
# LAMBDA_FUNCTION_NAME = 'cloudproject-function'
# LAMBDA_REGION = 'us-east-1'  

# s3 = boto3.client('s3', region_name='us-west-1')
# lambda_client = boto3.client('lambda', region_name=LAMBDA_REGION)

# @app.route('/')
# def index():
#     return render_template('index.html')

# @app.route('/upload', methods=['POST'])
# def upload():
#     if 'file' not in request.files:
#         flash('No file part')
#         return redirect(request.url)
    
#     file = request.files['file']
#     if file.filename == '':
#         flash('No selected file')
#         return redirect(request.url)
    
#     if file:
#         filename = secure_filename(file.filename)
#         filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
#         file.save(filepath)
        
#         # Upload to S3
#         s3.upload_file(filepath, S3_BUCKET, filename)
        
#         # Get emails
#         emails = request.form.get('emails').split(',')
        
#         # Prepare payload for Lambda function
#         payload = {
#             'filename': filename,
#             'emails': emails,
#             'uploaded_by': 'user@example.com'
#         }
 
#         try:
#             response = lambda_client.invoke(
#                 FunctionName=LAMBDA_FUNCTION_NAME,
#                 InvocationType='RequestResponse',
#                 Payload=json.dumps(payload)
#             )
#             response_payload = json.loads(response['Payload'].read())
#             if response_payload['statusCode'] == 200:
#                 flash('File uploaded and emails sent successfully')
#             else:
#                 flash(f"Error: {response_payload['body']}")
#         except Exception as e:
#             flash(f"Error invoking Lambda function: {str(e)}")
        
#         return redirect(url_for('index'))

# if __name__ == '__main__':
#     app.run(host='0.0.0.0', port=5000, debug=True)
