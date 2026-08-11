Absolutely. I’ve re-validated the current landscape and I’d structure the concept as a **technical product specification**, not just an idea note.

One important correction from our earlier discussion: the market has moved quickly. There are now several competitors doing basic comparison, and **Smartprix launched a quick-commerce comparison tool in July 2026** that compares cart-level totals and flags out-of-stock items. So the documentation below treats those as existing capabilities and defines your product around the deeper **basket optimization** layer rather than claiming basic comparison is novel. ([Smartprix][1])

Also, the data acquisition situation is now clear: a third-party **QuickCommerce API** currently exposes real-time product search, MRP, offer price, availability, inventory and delivery ETA across Blinkit, Zepto, Instamart, BigBasket and other platforms. It is not an official unified API from those four companies, but it makes the proposed V1 technically feasible. ([QuickCommerce API][2])

# Universal Cart Optimizer

## Product, Feature, Algorithm & Technical Architecture Documentation

**Document status:** Product/Technical Specification
**Target:** Flutter mobile app + Python/FastAPI backend
**Primary market:** India
**Primary platforms:** Blinkit, Zepto, Swiggy Instamart, BigBasket
**Core promise:**

> **Give me my shopping list. I'll tell you the cheapest, fastest and simplest way to buy all of it.**

---

# 1. Product Vision

The application is not fundamentally a "price comparison app."

The product should solve this problem:

> **A user has a list of products they need. Different quick-commerce platforms have different prices, stock, delivery times, discounts and fees. The application determines the best way to fulfil the entire list.**

The user should not have to:

* open Blinkit
* search every product
* remember prices
* open Zepto
* search again
* check Instamart
* calculate totals
* check BigBasket
* calculate delivery charges
* figure out which products are missing
* manually decide whether splitting an order is worth it

The system performs that work.

---

# 2. Core User Flow

```text
                    USER
                     │
                     ▼
             Creates shopping list
                     │
                     ▼
          "I need these 12 products"
                     │
                     ▼
             Product Normalization
                     │
                     ▼
          Canonical Product Mapping
                     │
                     ▼
        ┌────────────┼────────────┐
        ▼            ▼            ▼
     Blinkit       Zepto      Instamart
        │            │            │
        └────────────┼────────────┘
                     │
                  BigBasket
                     │
                     ▼
             Live Data Collection
                     │
          ┌──────────┼──────────┐
          ▼          ▼          ▼
        Price      Stock       ETA
          │          │          │
          └──────────┼──────────┘
                     ▼
              Offer/Fee Engine
                     │
                     ▼
             Cart Optimization
                     │
                     ▼
          ┌──────────┼──────────┐
          ▼          ▼          ▼
       Cheapest   One-Order    Fastest
          │          │          │
          └──────────┼──────────┘
                     ▼
             USER DECISION
                     │
                     ▼
             Open selected app
```

---

# 3. Product Philosophy

The application should answer only three questions:

### Question 1

> **Where can I get everything?**

### Question 2

> **What will I actually pay?**

### Question 3

> **What's the best combination?**

Everything else supports these three questions.

---

# 4. High-Confidence Feature Set

Below I am deliberately including only features for which the current data landscape gives us a **high-confidence YES**.

## 4.1 Shopping List

User can create:

```text
Milk
Eggs
Bread
Paneer
Tomatoes
Onions
Maggi
Coke
Shampoo
```

Features:

* Add product
* Remove product
* Quantity
* Edit quantity
* Search product
* Save shopping list
* Reuse previous list
* Clear list

---

# 5. Location-Based Comparison

Quick-commerce inventory is location dependent.

Therefore:

```text
User Location
      ↓
Latitude / Longitude
      ↓
Platform serviceability
      ↓
Nearest fulfilment location
      ↓
Price + inventory + ETA
```

The API currently supports location-specific searches using latitude/longitude and platform selection. ([QuickCommerce API][3])

The application should therefore never say simply:

> "Milk is available on Zepto."

It should say:

> **"Milk is available on Zepto at your selected location."**

---

# 6. Product Search

User enters:

> Amul Taaza 1L

Backend searches supported platforms.

Possible responses:

```text
Blinkit
Amul Taaza Toned Milk
1 L
₹64
Available

Zepto
Amul Taaza Milk
1 L
₹63
Available

Instamart
Amul Taaza Toned Milk
1 L
₹65
Available

BigBasket
Amul Taaza
1 L
₹62
Available
```

Current third-party API documentation supports product search across the major quick-commerce platforms. ([QuickCommerce API][3])

---

# 7. Product Normalization

This is one of the most important components.

Different platforms can describe the same product differently.

Example:

```text
Blinkit:
Amul Taaza Toned Milk 1L

Zepto:
Amul Taaza Milk 1000 ml

Instamart:
Amul Taaza Toned Milk - 1 litre

BigBasket:
Amul Taaza Toned Milk 1 Litre
```

These should become:

```text
CANONICAL PRODUCT

brand = Amul
product = Taaza Toned Milk
quantity = 1000
unit = ml
category = Milk
```

---

# 8. Product Matching Algorithm

## Step 1 — Normalize text

```text
lowercase
remove punctuation
remove unnecessary words
normalize units
normalize spelling
```

Example:

```text
"Amul Taaza Toned Milk - 1 Litre"

        ↓

"amul taaza toned milk 1000 ml"
```

---

## Step 2 — Extract attributes

```text
Brand
Product
Variant
Flavour
Quantity
Unit
Pack count
Category
```

Example:

```text
Brand: Amul
Product: Butter
Variant: Salted
Weight: 500g
```

---

## Step 3 — Match candidates

Use:

```text
Brand similarity
+
Product-name similarity
+
Variant similarity
+
Quantity compatibility
+
Unit compatibility
+
Category compatibility
```

---

## Step 4 — Confidence score

For example:

```text
Match Score =

0.30 × Brand Similarity
+
0.30 × Product Similarity
+
0.15 × Variant Similarity
+
0.15 × Quantity Similarity
+
0.10 × Category Similarity
```

Then:

```text
Score >= 0.90
    → Exact/very high confidence

0.75–0.89
    → Probable match

0.60–0.74
    → Show as possible alternative

< 0.60
    → Don't match
```

**Important:** These weights are proposed algorithm parameters, not externally measured values. They should later be tuned using real matching data.

---

# 9. Exact Product vs Alternative Product

The system must never blindly compare:

```text
Amul Butter 100g
```

against:

```text
Amul Butter 500g
```

Instead:

```text
EXACT MATCH
Amul Butter 100g

ALTERNATIVE
Amul Butter 500g
```

This distinction is critical.

A competitor's own users have reported concerns around price accuracy and product matching, which makes this a potentially important quality differentiator. ([Google Play][4])

---

# 10. Price Data

For every matched product:

```text
MRP
Selling Price
Offer Price
Discount
Platform
Timestamp
```

Example:

```text
MRP              ₹100
Current price     ₹78
Product saving    ₹22
Discount          22%
```

The current QuickCommerce API explicitly documents MRP, offer price and availability. ([QuickCommerce API][3])

---

# 11. Price-per-Unit Normalization

This is extremely important.

Example:

```text
Product A
₹120 / 500g

Product B
₹210 / 1kg
```

Users might think:

> ₹120 is cheaper.

But:

```text
A = ₹240/kg
B = ₹210/kg
```

Therefore:

```text
normalized_price =
price / quantity
```

Supported units:

```text
g → kg
ml → L
mg → g
```

Example:

```text
₹120 / 500g

= ₹0.24/g
= ₹240/kg
```

This allows a true value comparison.

---

# 12. Availability Engine

For every product/platform combination:

```text
AVAILABLE
OUT_OF_STOCK
NOT_SERVICEABLE
NOT_FOUND
UNKNOWN
```

Do not treat all failures as "out of stock."

For example:

```text
Zepto:
product not returned
```

could mean:

* genuinely unavailable
* search mismatch
* API failure
* location not supported
* temporary error

So internal state should be:

```text
availability_status
+
availability_confidence
+
last_checked_at
```

---

# 13. Delivery ETA

For every platform:

```text
Blinkit       12 min
Zepto         18 min
Instamart     15 min
BigBasket     32 min
```

The current API documentation exposes ETA for the quick-commerce platforms it supports. ([QuickCommerce API][3])

This allows:

### Fastest option

```text
MIN(ETA)
```

---

# 14. Single-Platform Algorithm

Suppose user needs:

```text
A
B
C
D
E
```

For every platform:

```text
Platform P
    ↓
Check A
Check B
Check C
Check D
Check E
```

Calculate:

```text
coverage =
available_items / total_items
```

Example:

```text
Blinkit = 5/5 = 100%
Zepto   = 4/5 = 80%
Instamart = 5/5 = 100%
BigBasket = 3/5 = 60%
```

Then only platforms satisfying:

```text
coverage = 100%
```

are eligible for:

### "Everything in one order"

---

# 15. Single-Order Total

For platform `P`:

```text
Product Total
+
Known Delivery Fee
+
Known Platform Fee
+
Known Handling Fee
-
Known Product Discounts
-
Verified Applicable Offers
```

Important:

> If an account-specific coupon cannot be verified, it must NOT be included as guaranteed savings.

Instead:

```text
Estimated potential saving
```

This protects the app from giving users false totals.

---

# 16. Multi-Platform Optimization

This is the heart of the product.

Suppose:

```text
Products:

A
B
C
D
E
F
```

Availability:

```text
             A B C D E F

Blinkit      ✓ ✓ ✓ ✗ ✓ ✓
Zepto        ✓ ✗ ✓ ✓ ✓ ✗
Instamart    ✓ ✓ ✗ ✓ ✓ ✓
BigBasket    ✓ ✓ ✓ ✓ ✓ ✓
```

BigBasket has everything.

But perhaps:

```text
BigBasket = ₹700
```

while:

```text
Blinkit + Zepto = ₹610
```

Then we need to discover the combination.

---

# 17. Multi-Cart Optimization Algorithm

Conceptually:

```text
                PRODUCTS
                    │
        ┌───────────┼───────────┐
        ▼           ▼           ▼
     Blinkit      Zepto      Instamart
        │           │           │
        └───────────┼───────────┘
                    ▼
             Generate feasible
                combinations
                    │
                    ▼
             Calculate total
                    │
                    ▼
             Rank combinations
```

---

# 18. Optimization Objective

For every candidate solution:

```text
Total Cost =
Σ product prices
+
Σ order-level fees
-
Σ applicable discounts
```

Then:

```text
Cheapest Solution
=
argmin(Total Cost)
```

---

# 19. But Cheapest Isn't Always Best

Suppose:

### Option A

```text
₹580
2 orders
```

### Option B

```text
₹595
1 order
```

Saving:

```text
₹15
```

But user may prefer one order.

Therefore we should provide multiple optimization modes.

---

# 20. Optimization Modes

## Mode A — Cheapest

Objective:

```text
minimize total payable amount
```

---

## Mode B — Minimum Orders

Objective:

```text
minimize number of platforms/orders
```

while keeping the total cost reasonable.

---

## Mode C — Fastest

Objective:

```text
minimize maximum delivery ETA
```

---

## Mode D — Best Overall

A weighted score:

```text
Score =
Cost Weight
+
Order Weight
+
ETA Weight
+
Coverage Weight
```

Example:

```text
Cost = 60%
Orders = 20%
ETA = 20%
```

These weights should eventually become user-configurable.

---

# 21. Better "Best Overall" Algorithm

Instead of hiding the mathematics, show the user the trade-off.

Example:

```text
OPTION 1
₹584
2 orders
15 min
CHEAPEST

OPTION 2
₹598
1 order
18 min
BEST OVERALL

OPTION 3
₹620
1 order
10 min
FASTEST
```

This is much more understandable.

---

# 22. Combination Search

For four platforms:

```text
Blinkit
Zepto
Instamart
BigBasket
```

the number of possible assignments grows.

For each product:

```text
Product → platform 1
Product → platform 2
Product → platform 3
Product → platform 4
```

Naive search is:

```text
P^N
```

where:

```text
P = platforms
N = products
```

For:

```text
4 platforms
10 products
```

naive combinations:

```text
4^10 = 1,048,576
```

Still possible for small carts, but unnecessary.

---

# 23. Better Optimization Algorithm

Use a **branch-and-bound / dynamic programming style optimizer**.

### Step 1

Remove unavailable product/platform combinations.

### Step 2

Find mandatory products:

```text
Only available on one platform
```

These constrain the solution.

### Step 3

Group products by compatible platforms.

### Step 4

Calculate lower-bound cost.

### Step 5

Prune any branch that already costs more than the best known solution.

### Step 6

Return top solutions.

---

# 24. Example

User needs:

```text
Milk
Eggs
Paneer
Bread
Oil
```

Availability:

```text
Milk       B Z I
Eggs       B Z
Paneer     Z I
Bread      B Z I
Oil        B I
```

The optimizer might discover:

```text
Blinkit:
Milk
Eggs
Bread
Oil

Zepto:
Paneer
```

Total:

```text
₹560
```

versus:

```text
Instamart:
Milk
Paneer
Bread
Oil

Zepto:
Eggs

₹575
```

and:

```text
BigBasket:
Everything

₹610
```

Result:

```text
CHEAPEST
₹560
2 orders

ONE ORDER
₹610
BigBasket

FASTEST
₹575
depending on ETA
```

---

# 25. Offer Engine

This should be a separate service.

```text
                CART
                  │
                  ▼
             Offer Engine
                  │
      ┌───────────┼───────────┐
      ▼           ▼           ▼
 Product      Cart-level   Platform
 discount      offer        offer
      │           │           │
      └───────────┼───────────┘
                  ▼
             Eligible offers
                  │
                  ▼
             Total savings
```

---

# 26. Offer Types

### Type A — Product discount

```text
MRP ₹100
Price ₹80

Saving ₹20
```

High confidence.

---

### Type B — Minimum-cart promotion

Example:

```text
₹100 OFF
above ₹999
```

If:

```text
Cart = ₹1,250
```

then:

```text
₹1,250 - ₹100
= ₹1,150
```

provided the offer is verified as applicable.

---

### Type C — Percentage discount

```text
10% off
maximum ₹100
minimum ₹799
```

Algorithm:

```text
discount =
min(cart × 10%, ₹100)
```

---

### Type D — First-order offer

This requires user eligibility.

Therefore:

```text
UNKNOWN
```

unless verified.

---

### Type E — Bank/payment offer

Also potentially account/payment-method dependent.

Do not automatically claim it.

---

# 27. Important Price-Confidence System

This is something I strongly recommend.

Every final amount should carry a confidence state.

### VERIFIED

```text
₹612
```

Data fully verified from available source.

### ESTIMATED

```text
₹612–₹650
```

Some fees/offers may depend on checkout.

### POTENTIAL SAVING

```text
Save up to ₹100
```

Offer exists but user eligibility isn't verified.

This prevents the biggest problem competitors appear to face: showing a comparison price that doesn't match the destination platform. Quick Compare's Google Play reviews specifically complain about displayed prices differing from actual prices. ([Google Play][4])

---

# 28. Final Cost Model

The internal model should be:

```text
FINAL_COST

=
PRODUCT_TOTAL

+ DELIVERY_FEE
+ PLATFORM_FEE
+ HANDLING_FEE
+ SMALL_CART_FEE

- PRODUCT_DISCOUNTS
- VERIFIED_CART_OFFERS
- VERIFIED_PLATFORM_OFFERS
```

Then:

```text
UNKNOWN_FEES
```

must remain separate.

Never silently assume:

```text
unknown = ₹0
```

---

# 29. User-Facing Result

The final screen should be extremely simple.

```text
YOUR CART

10 PRODUCTS

━━━━━━━━━━━━━━━━━━━━

BEST OVERALL

Instamart + Blinkit

₹612
10/10 products
2 orders
15–18 min

You save ₹86 vs
the best single-app option.

[ VIEW BREAKDOWN ]

━━━━━━━━━━━━━━━━━━━━

CHEAPEST

Zepto + Blinkit

₹584
2 orders

[ VIEW ]

━━━━━━━━━━━━━━━━━━━━

ONE ORDER

BigBasket

₹670
10/10 products

[ BUY ]

━━━━━━━━━━━━━━━━━━━━

FASTEST

Blinkit

₹648
9/10 products
11 min
```

---

# 30. Cost Breakdown

When user taps:

**View Breakdown**

show:

```text
BLINKIT

Milk             ₹60
Eggs             ₹90
Bread            ₹45
Oil             ₹140

Products         ₹335
Discount         -₹25
Delivery          ₹0
Platform fee      ₹5

Subtotal         ₹315
```

Then:

```text
ZEPTO

Paneer           ₹110
Shampoo          ₹180
Tomatoes          ₹45

Products         ₹335
Discount         -₹30
Delivery          ₹0

Total             ₹305
```

Then:

```text
TOTAL

₹620
```

---

# 31. "Why This Recommendation?" Feature

This is important for trust.

Show:

> **Recommended because:**

```text
₹58 cheaper than one-order option
Only 2 orders
All 12 products available
ETA under 20 minutes
```

Not:

> "AI says this is best."

The algorithm should be explainable.

---

# 32. Direct Purchase

Once user chooses:

```text
BUY
```

the application should open the corresponding platform/product deeplink.

Current data providers expose product deeplinks, and existing comparison apps already use redirect-to-platform workflows. ([QuickCommerce API][3])

---

# 33. Cart Transfer

Where technically and contractually supported:

```text
Our Cart
   ↓
Selected platform
   ↓
Replicate products
   ↓
Platform cart
   ↓
Checkout
```

But this should **not** be assumed as universally available.

V1 can simply provide:

> **Open in Blinkit**

and product links.

Later, supported cart-transfer mechanisms can be added.

---

# 34. Saved Lists

Examples:

```text
Weekly Groceries
Monthly Grocery
Gym Food
Hostel Shopping
Party
Breakfast
House Cleaning
```

User can run:

> **Compare Again**

The system fetches fresh prices/availability.

---

# 35. Recurring Basket Intelligence

For a saved basket:

```text
Last week:
₹720

Today:
₹651

You saved:
₹69
```

This creates long-term utility.

---

# 36. Price History

Potential future feature:

```text
Milk 1L

₹65
₹62
₹61
₹68
₹59
```

Current PriceBasket publicly offers price history and price alerts, so this should not be treated as unique. ([Pryzo][5])

It can nevertheless be useful as supporting functionality.

---

# 37. Price Alert

Example:

> Notify me when Amul Butter 500g goes below ₹230.

Again, this is a supporting feature rather than the core differentiation.

PriceBasket already offers price alerts and 30-minute monitoring according to its public FAQ. ([PriceBasket][6])

---

# 38. Architecture

## Frontend

```text
Flutter
│
├── Authentication
├── Location
├── Shopping List
├── Product Search
├── Comparison
├── Cart
├── Results
├── Offers
├── Saved Lists
└── Settings
```

---

# 39. Backend

```text
                    Flutter
                       │
                       ▼
                 API Gateway
                       │
                FastAPI Backend
                       │
      ┌────────────────┼────────────────┐
      │                │                │
      ▼                ▼                ▼
 Product Service   Cart Service    User Service
      │                │
      ▼                ▼
 Matching Engine   Optimizer
      │                │
      └────────┬───────┘
               ▼
          Offer Engine
               │
               ▼
        Data Aggregation Layer
               │
      ┌────────┼─────────┐
      ▼        ▼         ▼
   Blinkit   Zepto   Instamart
      │        │         │
      └────────┼─────────┘
               ▼
           BigBasket
```

---

# 40. Data Acquisition Layer

The most practical initial architecture is:

```text
                 Your Backend
                      │
                      ▼
             QuickCommerce API
                      │
      ┌───────────────┼───────────────┐
      ▼               ▼               ▼
   Blinkit          Zepto          Instamart
                                      │
                                  BigBasket
```

The current API documentation says it supports search/item operations across 11 platforms, including BlinkIt, Zepto, Swiggy, BigBasket, DMart, JioMart and Minutes, with ETA for the seven quick-commerce platforms. ([QuickCommerce API][3])

It also provides an API-key-based interface and charges credits per platform call. ([QuickCommerce API][2])

---

# 41. Important API Reality

There is currently **no single official public API from Blinkit + Zepto + Instamart + BigBasket that gives us everything we want.**

There is, however:

### Third-party aggregation

**YES**

### Product/price/availability/ETA

**YES**

### Public MRP/offer price

**YES**

### Verified user-specific coupon state

**NOT guaranteed**

### Guaranteed final checkout price for every user

**NOT guaranteed**

### Official Swiggy developer portal

**YES**, but its public portal currently does not expose a configured API category listing on the page, so we should not assume a freely available Instamart consumer-comparison endpoint from it. ([Swiggy Developer Portal][7])

---

# 42. Platform Terms Risk

This is critical.

For example, Zepto's current Terms explicitly prohibit accessing the platform through robots, spiders or other automated devices outside the provided interface. ([Zepto][8])

Therefore:

```text
DO NOT DESIGN THE BUSINESS AROUND:

our servers
   ↓
scrape Zepto
scrape Blinkit
scrape Instamart
scrape BigBasket
```

Instead:

```text
Licensed / approved API
        +
Official integrations
        +
Commercial data providers
        +
Deep links
```

The data-provider contract and each platform's current terms need legal review before production launch.

---

# 43. API Cost Optimization

This is important because your intended subscription is only:

```text
₹39–₹79
```

The current QuickCommerce API pricing is published in credits, with higher-volume plans reducing the per-call cost; its documentation says each platform call consumes a credit. ([QuickCommerce API][3])

We should therefore **never blindly do**:

```text
10 products
×
4 platforms
=
40 fresh calls
```

for every request.

Instead:

```text
User List
   ↓
Normalize
   ↓
Canonical Product
   ↓
Check Cache
   ↓
Only query missing/stale data
```

---

# 44. Caching Architecture

Use Redis.

```text
                  Request
                     │
                     ▼
                 Redis Cache
                  /       \
              HIT           MISS
               │              │
               ▼              ▼
             Return       API Provider
                              │
                              ▼
                            Store
                              │
                              ▼
                           Return
```

Cache key:

```text
platform
+
canonical_product_id
+
location_zone
```

Example:

```text
zepto:
amul_taaza_1l:
560001
```

---

# 45. Cache TTL

Because inventory changes rapidly:

### Availability

Short TTL.

```text
1–5 minutes
```

### Price

```text
5–15 minutes
```

### Product metadata

```text
hours/days
```

These are proposed engineering defaults, not guarantees from the providers.

---

# 46. Freshness Metadata

Every result should contain:

```text
checked_at
source
confidence
```

Example:

```text
₹62

Updated:
42 seconds ago
```

This gives users confidence.

---

# 47. Product Database

PostgreSQL.

Suggested tables:

```text
users

shopping_lists

shopping_list_items

canonical_products

platform_products

product_matches

price_snapshots

availability_snapshots

delivery_estimates

offers

offer_conditions

cart_solutions

platforms
```

---

# 48. Canonical Product Schema

```text
canonical_product

id
brand
name
category
subcategory
variant
flavour
quantity
unit
pack_count
barcode
normalized_name
created_at
updated_at
```

---

# 49. Platform Product Schema

```text
platform_product

id
platform
external_product_id
canonical_product_id
name
brand
variant
quantity
unit
mrp
selling_price
offer_price
availability
inventory
deeplink
image_url
rating
last_updated
```

---

# 50. Price Snapshot

```text
price_snapshot

id
platform_product_id
location_zone
mrp
selling_price
discount
timestamp
source
confidence
```

---

# 51. Offer Schema

```text
offer

id
platform
title
coupon_code
offer_type
discount_type
discount_value
max_discount
min_cart_value
start_time
end_time
eligible_categories
eligible_products
first_order_only
payment_method
combinable
source
confidence
```

---

# 52. Cart Optimization Engine

Inputs:

```text
Products
Quantities
Platforms
Availability
Prices
Discounts
Fees
Offers
ETA
User preferences
```

Output:

```text
solutions[]
```

Each solution:

```text
solution_id

platforms_used

items_by_platform

product_total

discount_total

delivery_total

fee_total

final_cost

estimated_savings

order_count

max_eta

confidence

explanation
```

---

# 53. Optimization Pseudocode

```text
INPUT:
    shopping_list
    platform_data
    user_preferences

1. Normalize all requested products

2. Match each product to platform products

3. Remove invalid/low-confidence matches

4. Build availability matrix

5. Remove unavailable combinations

6. Generate feasible platform assignments

7. For each assignment:
       calculate product total
       calculate product discounts
       calculate verified offers
       calculate delivery fees
       calculate platform fees
       calculate order count
       calculate ETA

8. Calculate final payable cost

9. Rank:
       cheapest
       fewest_orders
       fastest
       best_overall

10. Return top N solutions
```

---

# 54. Best-Overall Scoring

A possible initial scoring model:

```text
cost_score
eta_score
order_score
coverage_score
confidence_score
```

Then:

```text
overall_score =

0.55 × cost_score
+
0.20 × order_score
+
0.15 × eta_score
+
0.10 × confidence_score
```

Again, these are **initial tunable weights**, not empirically validated weights.

Later, user preferences can change them.

---

# 55. User Preference

Let user select:

```text
What matters most?

○ Cheapest
○ Fastest
○ One order
○ Balanced
```

Then:

### Cheapest

```text
Cost = 80%
```

### Fastest

```text
ETA = 70%
```

### One order

```text
Order count = 70%
```

This makes the app feel personalized without requiring AI.

---

# 56. AI Usage

AI should NOT be in the critical path.

The architecture should work without an LLM.

### AI can optionally help with:

```text
Messy user shopping requests
Natural-language shopping lists
Product matching fallback
Alternative-product explanations
Offer explanation
```

Example:

User:

> "Mere ghar mein 4 log hain, Sunday breakfast ke liye saman chahiye."

AI converts that into:

```text
Eggs
Bread
Milk
Butter
Jam
```

Then the deterministic shopping engine takes over.

---

# 57. Why AI Cost Can Stay Low

The core pipeline:

```text
API
+
PostgreSQL
+
Redis
+
Python algorithms
```

doesn't require an LLM.

AI should only process exceptional requests.

Therefore:

```text
1000 comparison requests
≈ 0 LLM calls
```

if the user uses the standard shopping-list workflow.

That's ideal for your ₹39–₹79 pricing model.

---

# 58. Competitor Landscape

I found a much more competitive market than we initially assumed.

The important competitors are:

1. Quick Compare
2. QuickV
3. Comparify
4. PriceBasket
5. Savvio
6. Compare Cart
7. ShopSwiftly
8. QuickChecky
9. PRyZO
10. Grabby
11. Smartprix Quick Commerce Comparison

---

# 59. Competitor: Quick Compare

[Quick Compare on Google Play](https://play.google.com/store/apps/details?hl=en&id=com.quickcompare.app&utm_source=chatgpt.com)

### Publicly documented functionality

* Blinkit
* Zepto
* Instamart
* Flipkart Minutes
* BigBasket
* price comparison
* availability
* delivery time
* real-time price comparison
* delivery estimates

### Traction

Current Google Play listing:

**500K+ downloads**

but only around **1.4/5 rating with ~580 reviews**. ([Google Play][4])

### Major weakness

User reviews specifically complain that:

> comparison price doesn't match the actual platform price.

That is extremely relevant to our product. ([Google Play][4])

### Strategic lesson

**Accuracy is potentially more valuable than having more platforms.**

---

# 60. Competitor: QuickV

[QuickV on Google Play](https://play.google.com/store/apps/details?hl=en&id=com.quickV.app&utm_source=chatgpt.com)

### Public functionality

* Blinkit
* Zepto
* Instamart
* BigBasket
* real-time price comparison
* delivery-time comparison
* categories
* hot deals
* unified multi-cart
* separate provider carts
* add items to multiple carts
* provider checkout
* cart optimizer
* coupon-aware positioning

Its website describes a cart optimizer that evaluates carts across providers and returns cheapest/fastest options. ([QuickV][9])

### Traction

Google Play shows **5K+ downloads** in its current listing, while AppBrain reports roughly 12K downloads and no ratings yet. ([Google Play][10])

### Strategic lesson

Very close to our intended architecture.

---

# 61. Competitor: Comparify

[Comparify](https://comparify.pro/grocery-price-comparison?utm_source=chatgpt.com)

This is probably the **most important competitor**.

### Grocery functionality

* Blinkit
* Zepto
* Instamart
* BigBasket
* JioMart
* DMart
* Flipkart Minutes
* DealShare
* MilkBasket
* Amazon Now where data is available
* product comparison
* availability
* delivery estimates
* saved comparisons
* carts
* account-specific prices according to its public positioning
* price comparison
* product matching

Its current website explicitly describes location-based comparison, product availability and delivery estimates. ([Comparify][11])

### Beyond grocery

It also compares:

* Uber
* Ola
* Rapido
* Namma Yatri
* Bharat Taxi

and food delivery platforms. ([App Store][12])

### Final-price positioning

Its developers have publicly described comparing final prices after coupons/fees in related comparison workflows. ([Reddit][13])

### Traction

Its current App Store listing shows:

**4.8/5 from 75 ratings.** ([App Store][12])

### Strategic lesson

This is not an idea we can beat merely by:

> “We compare Blinkit, Zepto and Instamart.”

We need a **better optimization/accuracy/trust layer**.

---

# 62. Competitor: PriceBasket

[PriceBasket](https://pricebasket.in/?utm_source=chatgpt.com)

### Public functionality

* 10+ apps
* Blinkit
* Zepto
* BigBasket
* Instamart
* JioMart
* DMart
* Amazon Fresh
* Flipkart Minutes
* price comparison
* price history
* price alerts
* shopping cart
* cart optimizer
* split-order optimization
* location-specific pricing

Its FAQ explicitly says the cart optimizer finds the cheapest combination of platforms to buy the entire list. ([PriceBasket][6])

### Strategic lesson

**Multi-cart optimization is already competitive territory.**

---

# 63. Competitor: Savvio

[Savvio on Google Play](https://play.google.com/store/apps/details?hl=en-US&id=app.savvio&utm_source=chatgpt.com)

### Public functionality

* Blinkit
* Instamart
* Zepto
* BigBasket
* Flipkart Minutes
* DMart
* JioMart
* price comparison
* real-time price tracking
* availability
* shopping list
* cart-value comparison
* product variants
* delivery time filtering
* price filtering
* deals

Google Play currently shows **5K+ downloads**. ([Google Play][14])

### Strategic lesson

Shopping-list comparison is already present.

---

# 64. Competitor: Compare Cart

[Compare Cart on Google Play](https://play.google.com/store/apps/details?id=com.goyal0ankit.comparecart&utm_source=chatgpt.com)

### Public functionality

* Blinkit
* Zepto
* Instamart
* JioMart
* Flipkart Grocery
* DMart
* location/pincode comparison
* price comparison
* shopping list
* favorites
* direct product redirects
* share cart

([Google Play][15])

### Strategic lesson

Basic comparison + list functionality isn't enough.

---

# 65. Competitor: ShopSwiftly

[ShopSwiftly on Google Play](https://play.google.com/store/apps/details?id=com.soartech.shopswiftly.shopswiftly&utm_source=chatgpt.com)

### Public functionality

* Instamart
* Blinkit
* BigBasket
* real-time comparison
* product information
* reviews/ratings
* direct comparison
* fastest/best deal positioning

Its App Store listing has shown a 3.4/5 rating from 17 ratings and user complaints about intrusive advertising. ([App Store][16])

An older Google Play listing showed **100K+ downloads**, so traction exists even though the current product positioning has evolved. ([Google Play][17])

---

# 66. Competitor: QuickChecky

[QuickChecky](https://quickchecky.com/?utm_source=chatgpt.com)

### Public functionality

* Blinkit
* Zepto
* Instamart
* real-time comparison
* price comparison
* savings
* product comparison
* availability

Public website currently claims:

**5K+ active users**
**4.8 rating**

These are company-provided claims rather than independently audited figures. ([QuickChecky][18])

---

# 67. Competitor: PRyZO

[PRyZO](https://www.pryzo.in/?utm_source=chatgpt.com)

### Public functionality

* Blinkit
* Zepto
* Instamart
* Amazon
* Flipkart
* JioMart
* 25+ platforms
* price comparison
* price history
* price alerts
* smart shopping lists
* cheapest platform per item
* community-powered prices

([Pryzo][5])

### Strategic lesson

The market is moving toward **multi-commerce aggregation**, not merely quick commerce.

---

# 68. Competitor: Grabby

[Grabby](https://grabby.co.in/?utm_source=chatgpt.com)

### Public functionality

* Blinkit
* Zepto
* Instamart
* price comparison
* real-time updates
* stock availability
* delivery time
* checkout-cost calculation
* delivery fees
* handling fees
* small-cart fees

Its positioning explicitly says it calculates final checkout amount rather than only item prices. ([Grabby][19])

---

# 69. Competitor: Smartprix

This one is particularly important because it is a large established comparison brand entering the space.

Smartprix launched a quick-commerce comparison tool in July 2026. It compares:

* Blinkit
* Zepto
* Instamart
* Flipkart Minutes
* BB Now
* Amazon Fresh
* groceries
* electronics
* mobile phones
* cart-level totals
* fees
* out-of-stock items

It is available through the Smartprix website/app and doesn't require login. ([Smartprix][1])

### Strategic implication

We are **not competing only with indie apps anymore.**

Established comparison brands can enter this category.

---

# 70. Competitor Comparison Matrix

| Product       |   Price | Availability |     ETA | Shopping List | Full Cart | Split Cart |    Fees |      Offers |     Price History |
| ------------- | ------: | -----------: | ------: | ------------: | --------: | ---------: | ------: | ----------: | ----------------: |
| Quick Compare |     Yes |          Yes |     Yes |       Limited |       Yes |          — | Limited |     Limited |                 — |
| QuickV        |     Yes |          Yes |     Yes |           Yes |       Yes |        Yes | Claimed |     Claimed |                 — |
| Comparify     |     Yes |          Yes |     Yes |           Yes |       Yes |        Yes |     Yes | Yes/claimed | Saved comparisons |
| PriceBasket   |     Yes |          Yes |     Yes |           Yes |       Yes |    **Yes** |       — |           — |           **Yes** |
| Savvio        |     Yes |          Yes |     Yes |       **Yes** |       Yes |          — |       — |       Deals |                 — |
| Compare Cart  | **Yes** |          Yes |       — |       **Yes** |       Yes |          — |       — |           — |                 — |
| ShopSwiftly   |     Yes |          Yes |     Yes |             — |       Yes |          — |       — |           — |                 — |
| QuickChecky   |     Yes |          Yes |     Yes |             — |         — |          — |       — |           — |                 — |
| PRyZO         |     Yes |          Yes |       — |       **Yes** |         — |          — |       — |           — |           **Yes** |
| Grabby        |     Yes |          Yes | **Yes** |           Yes |   **Yes** |          — | **Yes** |     **Yes** |                 — |
| Smartprix     | **Yes** |      **Yes** | **Yes** |       **Yes** |   **Yes** |          — | **Yes** |           — |                 — |

This table represents **publicly documented functionality**, not independently verified internal implementations. ([Google Play][4])

---

# 71. What Should Actually Differentiate Our Product?

After this research, I would **not** position the product as:

> "Compare grocery prices."

That is already crowded.

Instead:

# **"Optimize my entire purchase."**

The key difference becomes:

```text
Existing mindset:

Product
   ↓
Compare price
   ↓
Choose platform
```

Our mindset:

```text
Shopping List
      ↓
Understand exact products
      ↓
Check every platform
      ↓
Check availability
      ↓
Check price
      ↓
Check discounts
      ↓
Check fees
      ↓
Check ETA
      ↓
Evaluate single vs multiple orders
      ↓
Calculate total landed cost
      ↓
Generate best 3 options
      ↓
Explain why
      ↓
Send user to purchase
```

---

# 72. The Real Product Moat

Not AI.

Not Flutter.

Not the UI.

Not even the API.

The moat would eventually be:

### 1. Product matching accuracy

```text
Same product?
Same variant?
Same size?
Same pack?
```

### 2. Price accuracy

```text
Our price ≈ actual checkout price
```

### 3. Basket optimization

```text
Millions of possible combinations
→ best feasible solution
```

### 4. Offer intelligence

```text
Which offers actually apply?
```

### 5. Historical data

```text
Which platform tends to be cheaper
for this particular product?
```

### 6. User-specific intelligence

```text
User prefers:
one order
fast delivery
HDFC offers
Zepto
```

The system gradually becomes better at recommendations.

---

# 73. Final End-to-End Architecture

```text
                         ┌──────────────┐
                         │    FLUTTER   │
                         │     APP      │
                         └──────┬───────┘
                                │
                                ▼
                         ┌──────────────┐
                         │   FastAPI    │
                         │   Gateway    │
                         └──────┬───────┘
                                │
        ┌───────────────────────┼────────────────────────┐
        │                       │                        │
        ▼                       ▼                        ▼
┌───────────────┐       ┌───────────────┐       ┌───────────────┐
│ Shopping List │       │ Product Match │       │ User Profile  │
│    Service    │       │    Engine     │       │    Service    │
└───────┬───────┘       └───────┬───────┘       └───────────────┘
        │                       │
        └──────────────┬────────┘
                       ▼
                ┌───────────────┐
                │ Data Aggregator│
                └───────┬───────┘
                        │
          ┌─────────────┼──────────────┐
          ▼             ▼              ▼
       Blinkit        Zepto        Instamart
          │             │              │
          └─────────────┼──────────────┘
                        │
                    BigBasket
                        │
                        ▼
                ┌───────────────┐
                │  Redis Cache   │
                └───────┬───────┘
                        │
                        ▼
                ┌───────────────┐
                │ Offer Engine   │
                └───────┬───────┘
                        │
                        ▼
                ┌───────────────┐
                │ Cart Optimizer │
                └───────┬───────┘
                        │
             ┌──────────┼───────────┐
             ▼          ▼           ▼
          CHEAPEST    FASTEST    ONE ORDER
             │          │           │
             └──────────┼───────────┘
                        ▼
                ┌───────────────┐
                │ Recommendation│
                │    Engine     │
                └───────┬───────┘
                        │
                        ▼
                 USER DECISION
                        │
                        ▼
                 PLATFORM DEEPLINK
```

---

# 74. Recommended MVP

Despite everything above, **do not build all of it first.**

### Phase 1

Build only:

```text
Flutter
+
FastAPI
+
QuickCommerce API
+
Blinkit
+
Zepto
+
Instamart
+
BigBasket
```

Features:

* location
* shopping list
* product search
* product matching
* availability
* price
* MRP
* product discount
* ETA
* single-platform comparison
* multi-platform split optimization
* cheapest
* fastest
* one-order
* direct deeplink

This is already a complete product.

---

# 75. Phase 2

Add:

```text
Verified platform fees
Public offers
Cart-level discounts
Price confidence
Better product matching
Saved shopping lists
Price history
```

---

# 76. Phase 3

Add:

```text
User-specific offers
Account-aware pricing
More accurate final checkout estimation
Cart transfer
Payment-method optimization
```

Only after legitimate integrations/data access are established.

---

# 77. Phase 4

Expand beyond grocery:

```text
Amazon
Flipkart
JioMart
DMart
electronics
beauty
pharmacy* 
pet supplies
home products
```

For regulated categories such as pharmacy, the product would need a separate compliance/safety review.

---

# 78. The One-Screen Product Pitch

If I had to reduce the entire application to one screen:

```text
┌──────────────────────────────────┐
│                                  │
│       WHAT DO YOU NEED?          │
│                                  │
│  Milk                            │
│  Eggs                            │
│  Bread                           │
│  Paneer                          │
│  Tomatoes                        │
│  Oil                             │
│  Shampoo                         │
│                                  │
│       [ FIND BEST CART ]         │
│                                  │
└──────────────────────────────────┘
```

Then:

```text
┌──────────────────────────────────┐
│       BEST WAY TO BUY            │
│                                  │
│  ₹612                            │
│  Instamart + Blinkit             │
│                                  │
│  10/10 products                  │
│  2 orders                        │
│  15–18 min                       │
│                                  │
│  Save ₹86                        │
│                                  │
│       [ VIEW CART ]              │
│                                  │
└──────────────────────────────────┘
```

That's the entire value proposition.

---

# 79. Final Assessment

After doing the competitor and API research, my verdict is:

### **Technical feasibility: 8.5/10**

The core data required for V1 is currently obtainable through a third-party aggregation API. ([QuickCommerce API][2])

### **AI requirement: 2/10**

Very little AI is required.

### **AI cost potential: Very low**

The core algorithm is deterministic.

### **MVP difficulty: 6/10**

The engineering is manageable.

### **Data dependency: 9/10**

This is the biggest risk.

### **Competition: 8/10**

Much higher than we initially thought.

Quick Compare, QuickV, Comparify, PriceBasket, Savvio, Grabby and now Smartprix are already attacking substantial parts of the problem. ([Google Play][4])

### **Opportunity: 7/10**

There is clearly user demand, but we cannot win by simply being another comparison app.

### **The product I would build:**

> **A trusted basket optimizer that tells the user exactly how to fulfil an entire shopping list at the lowest practical total cost, while explicitly showing the trade-off between price, number of orders, delivery time and price confidence.**

The strongest differentiator is **not “we compare more apps.”**

It is:

> **“We solve the entire basket, not individual products.”**

And the most important engineering KPI should eventually be:

> **Displayed final cost vs actual checkout cost.**

If we can get that accuracy dramatically higher than the current low-rated competitors, *that* is a real product advantage rather than another feature checkbox.

[1]: https://www.smartprix.com/bytes/smartprixs-new-tool-finally-lets-you-price-compare-blinkit-zepto-and-instamart-before-you-order/?utm_source=chatgpt.com "Smartprix's New Tool Finally Lets You Price-Compare Blinkit, Zepto, and Instamart Before You Order - Smartprix"
[2]: https://quickcommerceapi.com/blog/getting-started-first-api-call?utm_source=chatgpt.com "Getting Started with QuickCommerce API: From Zero to First API Call in 5 Minutes | QuickCommerce API"
[3]: https://quickcommerceapi.com/docs?utm_source=chatgpt.com "API Documentation — Endpoints, Authentication & Examples | QuickCommerce API"
[4]: https://play.google.com/store/apps/details?hl=en&id=com.quickcompare.app&utm_source=chatgpt.com "Quick Compare - Apps on Google Play"
[5]: https://www.pryzo.in/?utm_source=chatgpt.com "PRyZO — Compare, Save and Buy"
[6]: https://pricebasket.in/faqs?utm_source=chatgpt.com "FAQs — PriceBasket Grocery Price Comparison | PriceBasket"
[7]: https://developers.swiggy.com/?utm_source=chatgpt.com "Swiggy Developer Portal"
[8]: https://www.zepto.com/terms-of-service?utm_source=chatgpt.com "Terms of Use - Zepto"
[9]: https://ciot.in/?utm_source=chatgpt.com "QuickV - India's Only Quick Commerce Aggregator"
[10]: https://play.google.com/store/apps/details?hl=en&id=com.quickV.app&utm_source=chatgpt.com "QuickV - Apps on Google Play"
[11]: https://comparify.pro/grocery-price-comparison?utm_source=chatgpt.com "Grocery Price Comparison Across Blinkit, Zepto, Instamart and More | Comparify"
[12]: https://apps.apple.com/in/app/comparify-cabs-groceries/id6757003836?utm_source=chatgpt.com "‎Comparify: Cabs & Groceries App - App Store"
[13]: https://www.reddit.com/r/IndiaSpeaks/comments/1t79top/built_a_free_app_to_compare_food_delivery_quick/?utm_source=chatgpt.com "Built a free app to compare food delivery, quick commerce and cab prices in one place"
[14]: https://play.google.com/store/apps/details?hl=en-US&id=app.savvio&utm_source=chatgpt.com "Savvio: Price Comparison App - Apps on Google Play"
[15]: https://play.google.com/store/apps/details?id=com.goyal0ankit.comparecart&utm_source=chatgpt.com "Compare Cart - Apps on Google Play"
[16]: https://apps.apple.com/in/app/shopswiftly-compare-e-marts/id6745510972?utm_source=chatgpt.com "‎ShopSwiftly: Compare E-Marts App - App Store"
[17]: https://play.google.com/store/apps/details?hl=en-US&id=com.soartech.shopswiftly.shopswiftly&utm_source=chatgpt.com "ShopSwiftly: Compare E-Marts - Apps on Google Play"
[18]: https://quickchecky.com/?utm_source=chatgpt.com "QuickChecky - Compare Blinkit, Zepto & Instamart Prices"
[19]: https://grabby.co.in/?utm_source=chatgpt.com "Grabby - Make Shopping Smarter"
