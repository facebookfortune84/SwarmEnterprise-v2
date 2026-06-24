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

    def cancel_hosting(self, project_id: str) -> Dict[str, Any]:
        """
        Cancels hosting subscription when a tenant is deleted.
        
        Args:
            project_id: Project ID to cancel hosting for
            
        Returns:
            Status dictionary with cancellation result
        """
        try:
            # Find subscription by project_id in metadata
            subscriptions = stripe.Subscription.list(limit=100)
            
            for subscription in subscriptions.data:
                if subscription.metadata.get("project_id") == project_id:
                    # Cancel the subscription
                    canceled_sub = stripe.Subscription.delete(subscription.id)
                    logger.info(f"Canceled subscription {subscription.id} for project {project_id}")
                    return {
                        "status": "success",
                        "subscription_id": subscription.id,
                        "canceled_at": canceled_sub.canceled_at
                    }
            
            logger.warning(f"No subscription found for project {project_id}")
            return {"status": "not_found", "message": "No subscription found"}
            
        except Exception as e:
            logger.error(f"Failed to cancel hosting for {project_id}: {e}")
            return {"status": "error", "message": str(e)}

# Global instance
payment_service = PaymentService()
