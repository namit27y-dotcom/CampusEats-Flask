-- ==========================================================
-- CampusEats - Real Backend Order Flow & Schema Migration
-- Ensures idempotent addition of all required columns across tables:
--   1. menu_items: stock_quantity, is_tracked
--   2. users: canteen_id
--   3. orders: razorpay_order_id, razorpay_payment_id, razorpay_signature
--   4. order_items: customization, extra_amount
-- ==========================================================

SET @dbname = DATABASE();

-- 1. menu_items.stock_quantity
SET @tablename = "menu_items";
SET @columnname = "stock_quantity";
SET @preparedStatement = (SELECT IF(
  (
    SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = @dbname
      AND TABLE_NAME = @tablename
      AND COLUMN_NAME = @columnname
  ) > 0,
  "SELECT 1",
  "ALTER TABLE menu_items ADD COLUMN stock_quantity INT NOT NULL DEFAULT 100;"
));
PREPARE alterIfNotExists FROM @preparedStatement;
EXECUTE alterIfNotExists;
DEALLOCATE PREPARE alterIfNotExists;

-- 2. menu_items.is_tracked
SET @columnname = "is_tracked";
SET @preparedStatement = (SELECT IF(
  (
    SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = @dbname
      AND TABLE_NAME = @tablename
      AND COLUMN_NAME = @columnname
  ) > 0,
  "SELECT 1",
  "ALTER TABLE menu_items ADD COLUMN is_tracked TINYINT(1) NOT NULL DEFAULT 0;"
));
PREPARE alterIfNotExists FROM @preparedStatement;
EXECUTE alterIfNotExists;
DEALLOCATE PREPARE alterIfNotExists;

-- 3. users.canteen_id
SET @tablename = "users";
SET @columnname = "canteen_id";
SET @preparedStatement = (SELECT IF(
  (
    SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = @dbname
      AND TABLE_NAME = @tablename
      AND COLUMN_NAME = @columnname
  ) > 0,
  "SELECT 1",
  "ALTER TABLE users ADD COLUMN canteen_id INT NULL DEFAULT NULL AFTER role;"
));
PREPARE alterIfNotExists FROM @preparedStatement;
EXECUTE alterIfNotExists;
DEALLOCATE PREPARE alterIfNotExists;

-- 4. orders.razorpay_order_id
SET @tablename = "orders";
SET @columnname = "razorpay_order_id";
SET @preparedStatement = (SELECT IF(
  (
    SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = @dbname
      AND TABLE_NAME = @tablename
      AND COLUMN_NAME = @columnname
  ) > 0,
  "SELECT 1",
  "ALTER TABLE orders ADD COLUMN razorpay_order_id VARCHAR(100) NULL AFTER payment_transaction_id;"
));
PREPARE alterIfNotExists FROM @preparedStatement;
EXECUTE alterIfNotExists;
DEALLOCATE PREPARE alterIfNotExists;

-- 5. orders.razorpay_payment_id
SET @columnname = "razorpay_payment_id";
SET @preparedStatement = (SELECT IF(
  (
    SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = @dbname
      AND TABLE_NAME = @tablename
      AND COLUMN_NAME = @columnname
  ) > 0,
  "SELECT 1",
  "ALTER TABLE orders ADD COLUMN razorpay_payment_id VARCHAR(100) NULL AFTER razorpay_order_id;"
));
PREPARE alterIfNotExists FROM @preparedStatement;
EXECUTE alterIfNotExists;
DEALLOCATE PREPARE alterIfNotExists;

-- 6. orders.razorpay_signature
SET @columnname = "razorpay_signature";
SET @preparedStatement = (SELECT IF(
  (
    SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = @dbname
      AND TABLE_NAME = @tablename
      AND COLUMN_NAME = @columnname
  ) > 0,
  "SELECT 1",
  "ALTER TABLE orders ADD COLUMN razorpay_signature VARCHAR(255) NULL AFTER razorpay_payment_id;"
));
PREPARE alterIfNotExists FROM @preparedStatement;
EXECUTE alterIfNotExists;
DEALLOCATE PREPARE alterIfNotExists;

-- 7. order_items.customization
SET @tablename = "order_items";
SET @columnname = "customization";
SET @preparedStatement = (SELECT IF(
  (
    SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = @dbname
      AND TABLE_NAME = @tablename
      AND COLUMN_NAME = @columnname
  ) > 0,
  "SELECT 1",
  "ALTER TABLE order_items ADD COLUMN customization TEXT NULL AFTER price;"
));
PREPARE alterIfNotExists FROM @preparedStatement;
EXECUTE alterIfNotExists;
DEALLOCATE PREPARE alterIfNotExists;

-- 8. order_items.extra_amount
SET @columnname = "extra_amount";
SET @preparedStatement = (SELECT IF(
  (
    SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = @dbname
      AND TABLE_NAME = @tablename
      AND COLUMN_NAME = @columnname
  ) > 0,
  "SELECT 1",
  "ALTER TABLE order_items ADD COLUMN extra_amount DECIMAL(10,2) NULL DEFAULT '0.00' AFTER customization;"
));
PREPARE alterIfNotExists FROM @preparedStatement;
EXECUTE alterIfNotExists;
DEALLOCATE PREPARE alterIfNotExists;

-- 9. Ensure default values for existing rows
UPDATE menu_items SET stock_quantity = 100 WHERE stock_quantity IS NULL;
UPDATE menu_items SET is_tracked = 0 WHERE is_tracked IS NULL;

-- 10. Assign unassigned kitchen/counter staff to existing valid canteens if any exist
UPDATE users u
JOIN (SELECT id FROM canteens WHERE is_active = 1 ORDER BY id ASC LIMIT 1) c
SET u.canteen_id = c.id
WHERE u.role IN ('kitchen', 'counter') AND u.canteen_id IS NULL;
