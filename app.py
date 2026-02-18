import streamlit as st
import pandas as pd
from datetime import datetime
import os
from dotenv import load_dotenv
import uuid
import base64
import json

# Load environment variables
load_dotenv()

# Page configuration
st.set_page_config(
    page_title="Streamlit PayPal Integration",
    page_icon="💰",
    layout="wide"
)

# Initialize session state
if 'cart' not in st.session_state:
    st.session_state.cart = []
if 'orders' not in st.session_state:
    st.session_state.orders = []
if 'payment_success' not in st.session_state:
    st.session_state.payment_success = False

# Product catalog
PRODUCTS = [
    {
        "id": "prod_001",
        "name": "Basic Plan",
        "price": 9.99,
        "description": "Perfect for individuals starting out",
        "features": ["Basic analytics", "5 projects", "Email support", "1 user"],
        "icon": "📊",
        "color": "#4CAF50"
    },
    {
        "id": "prod_002",
        "name": "Pro Plan",
        "price": 29.99,
        "description": "For professionals and small teams",
        "features": ["Advanced analytics", "Unlimited projects", "Priority support", "5 users", "API access"],
        "icon": "🚀",
        "color": "#2196F3"
    },
    {
        "id": "prod_003",
        "name": "Enterprise Plan",
        "price": 99.99,
        "description": "Full-featured for large organizations",
        "features": ["Enterprise analytics", "Unlimited everything", "24/7 phone support", "Unlimited users", "Custom integrations", "SLA guarantee"],
        "icon": "🏢",
        "color": "#9C27B0"
    }
]

# Custom CSS
st.markdown("""
    <style>
    /* Main container */
    .main-header {
        text-align: center;
        padding: 2rem;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 10px;
        margin-bottom: 2rem;
    }
    
    /* Product cards */
    .product-card {
        padding: 1.5rem;
        border-radius: 10px;
        border: 1px solid #e0e0e0;
        margin-bottom: 1rem;
        transition: transform 0.3s, box-shadow 0.3s;
        background: white;
    }
    
    .product-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 5px 20px rgba(0,0,0,0.1);
    }
    
    .product-icon {
        font-size: 3rem;
        margin-bottom: 1rem;
    }
    
    .product-name {
        font-size: 1.5rem;
        font-weight: bold;
        margin-bottom: 0.5rem;
    }
    
    .product-price {
        font-size: 2rem;
        color: #2ecc71;
        font-weight: bold;
        margin: 1rem 0;
    }
    
    .product-description {
        color: #666;
        margin-bottom: 1rem;
    }
    
    .feature-list {
        list-style-type: none;
        padding: 0;
        margin: 1rem 0;
    }
    
    .feature-list li {
        padding: 0.3rem 0;
        color: #555;
    }
    
    .feature-list li:before {
        content: "✓ ";
        color: #2ecc71;
        font-weight: bold;
    }
    
    /* PayPal button */
    .paypal-button {
        background: #0070ba;
        color: white;
        border: none;
        padding: 10px 20px;
        border-radius: 5px;
        cursor: pointer;
        font-size: 16px;
        width: 100%;
        transition: background 0.3s;
    }
    
    .paypal-button:hover {
        background: #005ea6;
    }
    
    /* Success message */
    .success-message {
        background: #d4edda;
        color: #155724;
        padding: 1rem;
        border-radius: 5px;
        border: 1px solid #c3e6cb;
        margin: 1rem 0;
    }
    
    /* Cart sidebar */
    .cart-item {
        padding: 0.5rem;
        border-bottom: 1px solid #eee;
    }
    
    .cart-total {
        font-size: 1.2rem;
        font-weight: bold;
        color: #2c3e50;
        margin-top: 1rem;
    }
    
    /* Stats cards */
    .stat-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 10px;
        text-align: center;
    }
    
    .stat-number {
        font-size: 2rem;
        font-weight: bold;
    }
    
    .stat-label {
        font-size: 0.9rem;
        opacity: 0.9;
    }
    </style>
""", unsafe_allow_html=True)

# Sidebar - Shopping Cart
with st.sidebar:
    st.markdown("### 🛒 Shopping Cart")
    
    if st.session_state.cart:
        for idx, item in enumerate(st.session_state.cart):
            col1, col2, col3 = st.columns([3, 1, 1])
            with col1:
                st.write(f"**{item['name']}**")
            with col2:
                st.write(f"${item['price']:.2f}")
            with col3:
                if st.button("❌", key=f"remove_{idx}"):
                    st.session_state.cart.pop(idx)
                    st.rerun()
        
        total = sum(item['price'] for item in st.session_state.cart)
        st.markdown(f"### Total: ${total:.2f}")
        
        if st.button("🔄 Clear Cart", use_container_width=True):
            st.session_state.cart = []
            st.rerun()
    else:
        st.info("Your cart is empty. Browse products to add items.")
    
    st.markdown("---")
    
    # Quick stats
    if st.session_state.orders:
        total_spent = sum(order['amount'] for order in st.session_state.orders)
        st.markdown("### 📊 Your Stats")
        st.markdown(f"**Orders:** {len(st.session_state.orders)}")
        st.markdown(f"**Total Spent:** ${total_spent:.2f}")

# Main content
st.markdown("""
    <div class="main-header">
        <h1>💰 Streamlit PayPal Integration</h1>
        <p>Complete payment solution for your Streamlit apps</p>
    </div>
""", unsafe_allow_html=True)

# Success message
if st.session_state.payment_success:
    st.markdown("""
        <div class="success-message">
            <h3>✓ Payment Successful!</h3>
            <p>Thank you for your purchase. You will receive a confirmation email shortly.</p>
        </div>
    """, unsafe_allow_html=True)
    st.session_state.payment_success = False

# Product display
st.markdown("## 📦 Our Products")

cols = st.columns(len(PRODUCTS))

for idx, product in enumerate(PRODUCTS):
    with cols[idx]:
        st.markdown(f"""
            <div class="product-card" style="border-top: 5px solid {product['color']}">
                <div class="product-icon">{product['icon']}</div>
                <div class="product-name">{product['name']}</div>
                <div class="product-description">{product['description']}</div>
                <div class="product-price">${product['price']:.2f}</div>
        """, unsafe_allow_html=True)
        
        # Features
        st.markdown("<ul class='feature-list'>", unsafe_allow_html=True)
        for feature in product['features']:
            st.markdown(f"<li>{feature}</li>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Add to cart button
        if st.button(f"➕ Add to Cart", key=f"add_{product['id']}"):
            st.session_state.cart.append({
                "id": product['id'],
                "name": product['name'],
                "price": product['price']
            })
            st.success(f"Added {product['name']} to cart!")
            st.rerun()

# Checkout section
if st.session_state.cart:
    st.markdown("---")
    st.markdown("## 💳 Checkout")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("### Payment Method")
        
        # Payment method selection
        payment_method = st.radio(
            "Select payment method:",
            ["PayPal", "Credit Card (via PayPal)", "PayPal Balance"],
            horizontal=True
        )
        
        st.markdown("### Order Summary")
        for item in st.session_state.cart:
            st.write(f"• {item['name']} - ${item['price']:.2f}")
        
        total = sum(item['price'] for item in st.session_state.cart)
        st.markdown(f"**Total: ${total:.2f}**")
    
    with col2:
        st.markdown("### Complete Payment")
        
        # Generate PayPal link
        invoice_number = f"INV-{uuid.uuid4().hex[:8].upper()}"
        
        # PayPal button HTML
        paypal_html = f"""
        <div style="text-align: center;">
            <form action="https://www.paypal.com/cgi-bin/webscr" method="post" target="_top">
                <input type="hidden" name="cmd" value="_cart">
                <input type="hidden" name="upload" value="1">
                <input type="hidden" name="business" value="{os.getenv('PAYPAL_BUSINESS_EMAIL', 'your-merchant@example.com')}">
                <input type="hidden" name="currency_code" value="USD">
                <input type="hidden" name="return" value="{os.getenv('APP_URL', 'http://localhost:8501')}/?success=true">
                <input type="hidden" name="cancel_return" value="{os.getenv('APP_URL', 'http://localhost:8501')}/?cancel=true">
                <input type="hidden" name="invoice" value="{invoice_number}">
        """
        
        # Add cart items to PayPal form
        for idx, item in enumerate(st.session_state.cart, 1):
            paypal_html += f"""
                <input type="hidden" name="item_name_{idx}" value="{item['name']}">
                <input type="hidden" name="amount_{idx}" value="{item['price']}">
                <input type="hidden" name="quantity_{idx}" value="1">
            """
        
        paypal_html += """
                <button type="submit" class="paypal-button">
                    <img src="https://www.paypalobjects.com/webstatic/en_US/i/buttons/checkout-logo-large.png" alt="Check out with PayPal" style="height: 30px;">
                </button>
            </form>
            
            <div style="margin-top: 20px;">
                <img src="https://www.paypalobjects.com/webstatic/mktg/logo/pp_cc_mark_37x23.jpg" alt="PayPal">
                <p style="font-size: 0.8rem; color: #666;">
                    Secure payment processed by PayPal<br>
                    <a href="#" onclick="alert('Demo mode - No actual payment will be processed!')">Test Payment</a>
                </p>
            </div>
        </div>
        """
        
        st.markdown(paypal_html, unsafe_allow_html=True)
        
        # Demo payment button
        if st.button("💰 Demo Payment (Test Mode)", use_container_width=True):
            # Simulate successful payment
            order = {
                "id": invoice_number,
                "items": st.session_state.cart.copy(),
                "amount": total,
                "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "status": "completed"
            }
            st.session_state.orders.append(order)
            st.session_state.cart = []
            st.session_state.payment_success = True
            st.rerun()

# Payment history section
if st.session_state.orders:
    st.markdown("---")
    st.markdown("## 📋 Recent Orders")
    
    # Convert orders to DataFrame for display
    orders_data = []
    for order in st.session_state.orders[-5:]:  # Show last 5 orders
        orders_data.append({
            "Order ID": order['id'],
            "Items": ", ".join([item['name'] for item in order['items']]),
            "Amount": f"${order['amount']:.2f}",
            "Date": order['date'],
            "Status": order['status']
        })
    
    df = pd.DataFrame(orders_data)
    st.dataframe(df, use_container_width=True)

# Footer
st.markdown("---")
st.markdown("""
    <div style="text-align: center; color: #666;">
        <p>🔒 All payments are securely processed by PayPal. We never store your payment information.</p>
        <p>© 2024 Streamlit PayPal Integration Demo</p>
    </div>
""", unsafe_allow_html=True)
