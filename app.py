import os
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from dotenv import load_dotenv
import paypalrestsdk
import uuid

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key-change-this')

# Configure PayPal
paypalrestsdk.configure({
    "mode": os.getenv('PAYPAL_MODE', 'sandbox'),  # sandbox or live
    "client_id": os.getenv('PAYPAL_CLIENT_ID'),
    "client_secret": os.getenv('PAYPAL_CLIENT_SECRET')
})

# Store created payments temporarily (in production, use a database)
payments = {}

@app.route('/')
def index():
    """Home page with product listing"""
    products = [
        {'id': 'prod1', 'name': 'Basic Plan', 'price': '9.99', 'description': 'Basic features for individuals'},
        {'id': 'prod2', 'name': 'Pro Plan', 'price': '29.99', 'description': 'Advanced features for professionals'},
        {'id': 'prod3', 'name': 'Enterprise Plan', 'price': '99.99', 'description': 'Complete solution for businesses'}
    ]
    return render_template('index.html', products=products)

@app.route('/create-payment', methods=['POST'])
def create_payment():
    """Create a PayPal payment and redirect to approval URL"""
    try:
        product_id = request.form.get('product_id')
        product_name = request.form.get('product_name')
        product_price = request.form.get('product_price')
        
        # Generate unique invoice number
        invoice_number = f"INV-{uuid.uuid4().hex[:8].upper()}"
        
        # Create payment object
        payment = paypalrestsdk.Payment({
            "intent": "sale",
            "payer": {
                "payment_method": "paypal"
            },
            "redirect_urls": {
                "return_url": url_for('execute_payment', _external=True),
                "cancel_url": url_for('cancel_payment', _external=True)
            },
            "transactions": [{
                "item_list": {
                    "items": [{
                        "name": product_name,
                        "sku": product_id,
                        "price": product_price,
                        "currency": "USD",
                        "quantity": 1
                    }]
                },
                "amount": {
                    "total": product_price,
                    "currency": "USD"
                },
                "description": f"Payment for {product_name}",
                "invoice_number": invoice_number
            }]
        })
        
        # Create payment
        if payment.create():
            # Store payment info temporarily
            payments[payment.id] = {
                'product_id': product_id,
                'product_name': product_name,
                'price': product_price,
                'invoice': invoice_number,
                'status': 'created'
            }
            
            # Extract approval URL
            for link in payment.links:
                if link.rel == "approval_url":
                    return redirect(link.href)
        else:
            return render_template('payment.html', error=f"Payment creation failed: {payment.error}")
            
    except Exception as e:
        return render_template('payment.html', error=str(e))

@app.route('/execute-payment')
def execute_payment():
    """Execute payment after user approval on PayPal"""
    payment_id = request.args.get('paymentId')
    payer_id = request.args.get('PayerID')
    
    if not payment_id or not payer_id:
        return redirect(url_for('index'))
    
    # Execute the payment
    payment = paypalrestsdk.Payment.find(payment_id)
    
    if payment.execute({"payer_id": payer_id}):
        # Payment successful
        payment_info = payments.get(payment_id, {})
        
        # In production, save to database here
        payment_info['status'] = 'completed'
        payment_info['paypal_payment_id'] = payment_id
        payment_info['payer_id'] = payer_id
        
        return render_template('success.html', 
                             payment_info=payment_info,
                             transaction_id=payment_id)
    else:
        return render_template('payment.html', 
                             error=f"Payment execution failed: {payment.error}")

@app.route('/cancel-payment')
def cancel_payment():
    """Handle payment cancellation"""
    payment_id = request.args.get('paymentId')
    
    if payment_id and payment_id in payments:
        payments[payment_id]['status'] = 'cancelled'
    
    return render_template('payment.html', 
                         message="Payment was cancelled. No charges were made.")

@app.route('/payment-status/<payment_id>')
def payment_status(payment_id):
    """Check payment status"""
    if payment_id in payments:
        return jsonify(payments[payment_id])
    return jsonify({'error': 'Payment not found'}), 404

@app.route('/donate')
def donate():
    """Simple donation page with PayPal button"""
    paypal_dict = {
        "business": "your-merchant-email@example.com",  # Your PayPal merchant email
        "amount": "10.00",
        "item_name": "Donation",
        "currency_code": "USD",
        "no_shipping": "1",
        "return": url_for('donation_success', _external=True),
        "cancel_return": url_for('donation_cancel', _external=True),
    }
    return render_template('donate.html', paypal_dict=paypal_dict)

@app.route('/donation-success')
def donation_success():
    """Donation success page"""
    return render_template('success.html', 
                         message="Thank you for your donation!")

@app.route('/donation-cancel')
def donation_cancel():
    """Donation cancellation page"""
    return render_template('payment.html', 
                         message="Donation cancelled. Thank you for considering!")

if __name__ == '__main__':
    app.run(debug=True, port=5000)
