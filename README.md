# Sale Order API Integration

An Odoo module for managing sale orders through API integration with PrintAI/Production systems and Infor.

## Overview

This module extends Odoo's `sale.order` model to provide API endpoints for creating and updating sale orders from external systems, primarily PrintAI and production management systems.

## System Architecture

The integration follows this workflow:

1. **Sales Order** → Odoo
2. **Production Order** → Odoo
3. **Production Status Updates** → Odoo
4. **Production Completion** → Odoo
5. **ASN (Advance Shipping Notice)** → Infor
6. **Shipment Confirmation** → Infor

## Key Features

- **Create Sale Orders**: API endpoint to create new sale orders with validation
- **Update Sale Orders**: API endpoint to update existing sale orders
- **Timezone Handling**: Automatic localization of datetime fields
- **Product Management**: Auto-creation of products if not found
- **Analytic Accounting**: Automatic analytic tag assignment
- **Global Discounts**: Support for order-level discounts
- **Charge Lines**: Support for additional charges
- **Parent-Child Products**: Support for ISBN parent-child relationships

## Required Parameters

### For Sale Order Creation:

- `origin`: Unique sale order reference
- `partner_code`: Customer code
- `currency_code`: Currency identifier
- `order_line`: Array of order line items
  - `default_code`: Product code
  - `product_group`: Product group code
  - `account_type`: Account type classification
  - `order_type`: Order type classification

## API Methods

### `create_api(data)`

Creates a new sale order and confirms it automatically.

### `update_api(data, origin)`

Updates an existing sale order by origin reference.

### `prepare_data_create_api(data)`

Validates and prepares data for sale order creation.

### `prepare_data_update_api(data)`

Validates and prepares data for sale order updates.

## Error Handling

The module includes comprehensive validation:

- Duplicate order prevention
- Required parameter validation
- Product existence verification
- Currency and partner validation
- Company configuration checks

## Dependencies

- Odoo ERP system
- Python libraries: `pytz`, `json`
- Custom models: `product.group`, `account.analytic.default`

## Configuration

Ensure the following are configured in Odoo:

- Company global discount product
- Product categories for finished goods
- Analytic accounting defaults
- Currency and pricelist setup
