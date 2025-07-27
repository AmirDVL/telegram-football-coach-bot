-- Add admin user to PostgreSQL database
INSERT INTO admins (user_id, permissions, added_by) 
VALUES (293893885, '{"can_manage_users": true, "can_manage_payments": true, "can_view_stats": true, "is_super_admin": true}', 293893885) 
ON CONFLICT (user_id) DO NOTHING;
