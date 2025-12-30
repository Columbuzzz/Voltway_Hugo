# Voltway Hugo - Email SOP (Standard Operating Procedures)

This document defines the handling procedures for different email types received by Hugo.

---

## Email Intent Categories

Hugo classifies incoming supplier emails into these categories:

| Intent | Description | Risk Range |
|--------|-------------|------------|
| **DELAY** | Shipment or delivery date postponement | 2-5 |
| **PRICE_CHANGE** | Cost increase or decrease notification | 2-4 |
| **QUALITY_ALERT** | Defects, recalls, or quality issues | 3-5 |
| **CANCELLATION** | Order cancellation by supplier | 4-5 |
| **DISCONTINUATION** | Part end-of-life notification | 4-5 |
| **PARTIAL_SHIPMENT** | Incomplete order fulfillment | 2-3 |
| **NEW_PROPOSAL** | New supplier offer or quote | 1-2 |
| **DEMAND_CHANGE** | Customer demand modification | 2-4 |
| **OTHER** | Unclassified communications | 1-3 |

---

## Risk Score Definitions

| Score | Level | Response Time | Description |
|-------|-------|---------------|-------------|
| 1 | Low | 48 hours | Informational, no action required |
| 2 | Moderate | 24 hours | Monitor, potential future impact |
| 3 | Elevated | 12 hours | Action required, production at risk |
| 4 | High | 4 hours | Urgent action, line stop possible |
| 5 | Critical | Immediate | Production halted, escalate now |

---

## SOP by Email Intent

### 1. DELAY
**Trigger:** Supplier notifies of shipment delay

**Actions:**
1. Query `material_orders` for affected order details
2. Check `stock_levels` for current inventory buffer
3. Calculate days of coverage with `check_fulfillment`
4. If buffer < lead time:
   - Alert procurement team
   - Search for alternate suppliers in `suppliers` table
   - Calculate expedite cost vs. line stop cost

**Hugo Commands:**
```
"What's the delay on order O5007?"
"Can we still build S1_V1 units if P300 is delayed by 10 days?"
```

---

### 2. PRICE_CHANGE
**Trigger:** Supplier notifies of price increase/decrease

**Actions:**
1. Extract old_value and new_value from email
2. Calculate impact: `(new_price - old_price) * pending_order_qty`
3. Query historical orders for volume leverage
4. If increase > 5%:
   - Flag for procurement review
   - Compare against alternate supplier pricing

**Hugo Commands:**
```
"What price changes have we received this month?"
"How much would a 10% increase on P305 cost us?"
```

---

### 3. QUALITY_ALERT
**Trigger:** Supplier reports quality issues, recalls, or defects

**Actions:**
1. **IMMEDIATE:** Update `stock_levels` to set `status='HOLD'`
2. Query `stock_movements` to trace affected inventory
3. Check `sales_orders` for impacted customer shipments
4. Quarantine affected parts by warehouse location
5. Notify quality team for inspection protocol

**Hugo Commands:**
```
"Which orders used parts from lot P323?"
"Put all P323 stock on quality hold"
```

---

### 4. CANCELLATION
**Trigger:** Supplier cancels a pending order

**Actions:**
1. Calculate fulfillment gap with `check_fulfillment`
2. Immediately search `suppliers` for alternatives
3. Calculate `safety_stock` requirements
4. Escalate to procurement manager if critical part
5. Update `material_orders` status

**Hugo Commands:**
```
"Which suppliers can provide P312 besides current one?"
"How long until we run out of P312 without this order?"
```

---

### 5. DISCONTINUATION
**Trigger:** Part reaching end-of-life, will no longer be manufactured

**Actions:**
1. Calculate total lifetime demand from `sales_orders` history
2. Recommend last-time-buy quantity
3. Flag engineering for redesign consideration
4. Search for drop-in replacement parts
5. Update BOM notes

**Hugo Commands:**
```
"What's our projected demand for P324 over next 12 months?"
"Search specs for LCD display alternatives"
```

---

### 6. PARTIAL_SHIPMENT
**Trigger:** Order arriving with less quantity than expected

**Actions:**
1. Update `material_orders` with actual received quantity
2. Recalculate `stock_levels` projections
3. Determine if partial covers immediate needs
4. Request backorder timeline from supplier
5. Adjust production schedule if needed

**Hugo Commands:**
```
"Update order O5010 - received 80 of 100 units"
"Can we build 50 S2_V2 with current partial shipment?"
```

---

### 7. DEMAND_CHANGE
**Trigger:** Customer changes order quantity or timing

**Actions:**
1. Update `sales_orders` with new requirements
2. Recalculate material requirements
3. Check if existing orders cover new demand
4. Identify expedite or defer opportunities
5. Communicate with suppliers if major change

**Hugo Commands:**
```
"Customer increased S3_V1 order from 100 to 150 units"
"Do we have enough parts for the increased demand?"
```

---

## Escalation Matrix

| Risk Level | Escalation Path |
|------------|-----------------|
| 1-2 | Log only, no escalation |
| 3 | Notify Procurement Lead |
| 4 | Notify Procurement Manager + Operations |
| 5 | C-Level alert + War room activation |

---

## Hugo Query Examples

**Stock Awareness:**
```
"What's our current stock situation?"
"Which parts are running low?"
"Show me stock for all S2_V2 components"
```

**Email Awareness:**
```
"What emails came in today?"
"Any high-risk supplier issues?"
"Search emails about quality alerts"
"Show me details about the delay email"
```

**Combined Intelligence:**
```
"Are there any stock issues related to recent emails?"
"What's the status of parts mentioned in today's supplier communications?"
```
