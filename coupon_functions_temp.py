    async def process_toggle_coupon(self, query) -> None:
        """Process toggling a specific coupon"""
        await query.answer()
        
        coupon_code = query.data.replace('toggle_coupon_', '')
        success = self.coupon_manager.toggle_coupon(coupon_code)
        
        if success:
            coupons = self.coupon_manager.get_all_coupons()
            coupon = coupons.get(coupon_code, {})
            status = "فعال" if coupon.get('active', False) else "غیرفعال"
            text = f"✅ وضعیت کد تخفیف {coupon_code} به {status} تغییر یافت!"
        else:
            text = f"❌ خطا در تغییر وضعیت کد تخفیف {coupon_code}"
        
        keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data='admin_coupons')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup)

    async def process_delete_coupon(self, query) -> None:
        """Process deleting a specific coupon"""
        await query.answer()
        
        coupon_code = query.data.replace('delete_coupon_', '')
        success = self.coupon_manager.delete_coupon(coupon_code)
        
        if success:
            text = f"✅ کد تخفیف {coupon_code} با موفقیت حذف شد!"
        else:
            text = f"❌ خطا در حذف کد تخفیف {coupon_code}"
        
        keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data='admin_coupons')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup)
