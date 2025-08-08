### SQL queries for leads and messages

Notes:
- Assumes PostgreSQL.
- Parameters use named placeholders (e.g., `:lead_category_name`, `:start_ts`, `:end_ts`).
- Joins prefer direct references on `detected_leads` when present and fall back to `message_intent_classifications` via `COALESCE(...)` for backward compatibility.
- Filters `whatsapp_messages.is_real = TRUE` to exclude synthetic/test data.

---

#### 1) Find all messages with a given lead_category name

```sql
SELECT
  wm.id,
  wm.message_id,
  wm.timestamp,
  wm.raw_text,
  wm.group_id,
  wg.group_name,
  lc.name AS lead_category
FROM detected_leads AS dl
LEFT JOIN message_intent_classifications AS mic
  ON mic.id = dl.classification_id
JOIN whatsapp_messages AS wm
  ON wm.id = COALESCE(dl.message_id, mic.message_id)
JOIN whatsapp_groups AS wg
  ON wg.id = COALESCE(dl.group_id, wm.group_id)
JOIN lead_categories AS lc
  ON lc.id = COALESCE(dl.lead_category_id, mic.lead_category_id)
WHERE LOWER(lc.name) = LOWER(:lead_category_name)
  AND wm.is_real = TRUE
ORDER BY wm.timestamp DESC;
```

---

#### 2) Find all messages from the last 7 days for a given lead_category name

```sql
SELECT
  wm.id,
  wm.message_id,
  wm.timestamp,
  wm.raw_text,
  wm.group_id,
  wg.group_name,
  lc.name AS lead_category
FROM detected_leads AS dl
LEFT JOIN message_intent_classifications AS mic
  ON mic.id = dl.classification_id
JOIN whatsapp_messages AS wm
  ON wm.id = COALESCE(dl.message_id, mic.message_id)
JOIN whatsapp_groups AS wg
  ON wg.id = COALESCE(dl.group_id, wm.group_id)
JOIN lead_categories AS lc
  ON lc.id = COALESCE(dl.lead_category_id, mic.lead_category_id)
WHERE LOWER(lc.name) = LOWER(:lead_category_name)
  AND wm.is_real = TRUE
  AND wm.timestamp >= NOW() - INTERVAL '7 days'
  AND wm.timestamp < NOW()
ORDER BY wm.timestamp DESC;
```

Tip: Replace the time window with explicit parameters as needed, e.g. `wm.timestamp >= :start_ts AND wm.timestamp < :end_ts`.

---

#### 3) Statistics per lead_category between dates
- For each lead category: total leads in range, and per-group breakdown within the category.

```sql
WITH leads_in_range AS (
  SELECT
    dl.id,
    COALESCE(dl.lead_category_id, mic.lead_category_id) AS lead_category_id,
    COALESCE(dl.group_id, wm.group_id) AS group_id,
    wm.timestamp
  FROM detected_leads AS dl
  LEFT JOIN message_intent_classifications AS mic
    ON mic.id = dl.classification_id
  JOIN whatsapp_messages AS wm
    ON wm.id = COALESCE(dl.message_id, mic.message_id)
  WHERE wm.is_real = TRUE
    AND wm.timestamp >= :start_ts
    AND wm.timestamp < :end_ts
)
SELECT
  lc.name AS lead_category,
  wg.group_name,
  wg.whatsapp_group_id,
  COUNT(*) AS leads_in_group,
  SUM(COUNT(*)) OVER (PARTITION BY lc.id) AS total_in_category
FROM leads_in_range AS lir
JOIN lead_categories AS lc
  ON lc.id = lir.lead_category_id
JOIN whatsapp_groups AS wg
  ON wg.id = lir.group_id
GROUP BY lc.id, lc.name, wg.group_name, wg.whatsapp_group_id
ORDER BY lc.name, leads_in_group DESC;
```

---

#### 4) Statistics per group between dates
- For each group: total messages, number of leads, and percentage of messages that are leads.

```sql
WITH msgs AS (
  SELECT wm.group_id, COUNT(*) AS total_msgs
  FROM whatsapp_messages AS wm
  WHERE wm.is_real = TRUE
    AND wm.timestamp >= :start_ts
    AND wm.timestamp < :end_ts
  GROUP BY wm.group_id
),
leads AS (
  SELECT COALESCE(dl.group_id, wm.group_id) AS group_id,
         COUNT(*) AS lead_msgs
  FROM detected_leads AS dl
  LEFT JOIN message_intent_classifications AS mic
    ON mic.id = dl.classification_id
  JOIN whatsapp_messages AS wm
    ON wm.id = COALESCE(dl.message_id, mic.message_id)
  WHERE wm.is_real = TRUE
    AND wm.timestamp >= :start_ts
    AND wm.timestamp < :end_ts
  GROUP BY COALESCE(dl.group_id, wm.group_id)
)
SELECT
  wg.id AS group_id,
  wg.group_name,
  COALESCE(m.total_msgs, 0) AS total_messages,
  COALESCE(l.lead_msgs, 0) AS lead_messages,
  CASE WHEN COALESCE(m.total_msgs, 0) > 0
       THEN ROUND((COALESCE(l.lead_msgs, 0)::numeric / m.total_msgs::numeric) * 100, 2)
       ELSE 0 END AS lead_percentage_in_group
FROM whatsapp_groups AS wg
LEFT JOIN msgs AS m ON m.group_id = wg.id
LEFT JOIN leads AS l ON l.group_id = wg.id
WHERE COALESCE(m.total_msgs, 0) > 0 OR COALESCE(l.lead_msgs, 0) > 0
ORDER BY lead_messages DESC;
```

---

#### 5) Overall lead statistics between dates

5a) Total number of leads
```sql
SELECT COUNT(*) AS total_leads
FROM detected_leads AS dl
LEFT JOIN message_intent_classifications AS mic
  ON mic.id = dl.classification_id
JOIN whatsapp_messages AS wm
  ON wm.id = COALESCE(dl.message_id, mic.message_id)
WHERE wm.is_real = TRUE
  AND wm.timestamp >= :start_ts
  AND wm.timestamp < :end_ts;
```

5b) Top 3 groups by leads
```sql
SELECT
  wg.id AS group_id,
  wg.group_name,
  COUNT(*) AS leads
FROM detected_leads AS dl
LEFT JOIN message_intent_classifications AS mic
  ON mic.id = dl.classification_id
JOIN whatsapp_messages AS wm
  ON wm.id = COALESCE(dl.message_id, mic.message_id)
JOIN whatsapp_groups AS wg
  ON wg.id = COALESCE(dl.group_id, wm.group_id)
WHERE wm.is_real = TRUE
  AND wm.timestamp >= :start_ts
  AND wm.timestamp < :end_ts
GROUP BY wg.id, wg.group_name
ORDER BY leads DESC
LIMIT 3;
```

5c) Top 3 lead categories by leads
```sql
SELECT
  lc.id AS lead_category_id,
  lc.name AS lead_category_name,
  COUNT(*) AS leads
FROM detected_leads AS dl
LEFT JOIN message_intent_classifications AS mic
  ON mic.id = dl.classification_id
JOIN lead_categories AS lc
  ON lc.id = COALESCE(dl.lead_category_id, mic.lead_category_id)
JOIN whatsapp_messages AS wm
  ON wm.id = COALESCE(dl.message_id, mic.message_id)
WHERE wm.is_real = TRUE
  AND wm.timestamp >= :start_ts
  AND wm.timestamp < :end_ts
GROUP BY lc.id, lc.name
ORDER BY leads DESC
LIMIT 3;
```

