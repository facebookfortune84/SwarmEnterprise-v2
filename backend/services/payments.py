"""
Payment Service - Handles Stripe subscriptions and hosting billing.
"""

import os
import logging
import stripe
from typing import Dict, Any

logger = logging.getLogger("PaymentService")

# Stripe configuration
stripe.api_key = os.getenv("STRIPE_API_KEY", "sk_test_placeholder")

class PaymentService:
    """
    Manages monetization for the sovereign factory.
    - Hosting subscriptions
    - One-time company generation fees
    - Usage-based billing
    """

    def __init__(self):
        self.hosting_price_id = os.getenv("STRIPE_HOSTING_PRICE_ID", "price_hosting_monthly")

    def create_hosting_subscription(self, customer_email: str, project_id: str) -> Dict[str, Any]:
        """
        Creates a recurring subscription for VM hosting.
        """
        try:
            # 1. Find or create customer
            customers = stripe.Customer.list(email=customer_email, limit=1).data
            if customers:
                customer = customers[0]
            else:
                customer = stripe.Customer.create(
                    email=customer_email,
                    metadata={"project_id": project_id}
                )

            # 2. Create subscription
            subscription = stripe.Subscription.create(
                customer=customer.id,
                items=[{"price": self.hosting_price_id}],
                metadata={"project_id": project_id, "type": "hosting"}
            )
            
            logger.info(f"Subscription created: {subscription.id} for {customer_email}")
            return {"status": "success", "subscription_id": subscription.id}
            
        except Exception as e:
            logger.error(f"Failed to create subscription: {e}")
            return {"status": "error", "message": str(e)}

    def cancel_hosting(self, project_id: str):
        """
        Cancels hosting subscription when a tenant is deleted.
        """
        # Logic to find subscription by metadata and cancel
        logger.info(f"Canceling hosting for {project_id}...")
        pass

# Global instance
payment_service = PaymentService()
