    async def show_user_course_plan_management_enhanced(self, query, user_id: str, course_code: str) -> None:
        """Enhanced version of plan management with main plan assignment"""
        try:
            await query.answer()
            
            # Load user data and plans
            with open('bot_data.json', 'r', encoding='utf-8') as f:
                bot_data = json.load(f)
            
            user_data = bot_data.get('users', {}).get(user_id, {})
            user_name = user_data.get('name', 'نامشخص')
            
            user_plans = await self.load_user_plans(user_id)
            course_plans = user_plans.get(course_code, [])
            
            course_names = {
                'online_weights': '🏋️ وزنه آنلاین',
                'online_cardio': '🏃 هوازی آنلاین',
                'online_combo': '💪 ترکیبی آنلاین',
                'in_person_cardio': '🏃‍♂️ هوازی حضوری',
                'in_person_weights': '🏋️‍♀️ وزنه حضوری',
                'nutrition_plan': '🥗 برنامه غذایی'
            }
            course_name = course_names.get(course_code, course_code)
            
            keyboard = [
                [InlineKeyboardButton("📤 آپلود برنامه جدید", callback_data=f'upload_user_plan_{user_id}_{course_code}')]
            ]
            
            text = f"📋 مدیریت برنامه {course_name}\n"
            text += f"👤 کاربر: {user_name}\n\n"
            
            if course_plans:
                # Check current main plan
                current_main_plan = await self.get_main_plan_for_user_course(user_id, course_code)
                
                text += f"📚 برنامه‌های موجود ({len(course_plans)} عدد):\n"
                if current_main_plan:
                    text += f"⭐ برنامه اصلی فعلی: {current_main_plan}\n"
                text += "\n"
                
                # Sort plans by created date (newest first)
                sorted_plans = sorted(course_plans, key=lambda x: x.get('created_at', ''), reverse=True)
                
                for i, plan in enumerate(sorted_plans, 1):
                    created_at = plan.get('created_at', 'نامشخص')[:16].replace('T', ' ')
                    plan_type = plan.get('content_type', 'document')
                    file_name = plan.get('filename', 'نامشخص')
                    plan_id = plan.get('id', f'plan_{i}')
                    
                    # Check if this is the main plan
                    is_main_plan = (current_main_plan == plan_id)
                    main_indicator = " ⭐ (برنامه اصلی)" if is_main_plan else ""
                    
                    text += f"{i}. 📄 {file_name}{main_indicator}\n"
                    text += f"   📅 {created_at}\n"
                    text += f"   📋 نوع: {plan_type}\n"
                    
                    # Create buttons for each plan
                    plan_buttons = [
                        InlineKeyboardButton(f"📤 ارسال {i}", callback_data=f'send_user_plan_{user_id}_{course_code}_{plan_id}'),
                        InlineKeyboardButton(f"🗑 حذف {i}", callback_data=f'delete_user_plan_{user_id}_{course_code}_{plan_id}')
                    ]
                    
                    # Add main plan toggle button
                    if is_main_plan:
                        plan_buttons.append(InlineKeyboardButton("❌ حذف از اصلی", callback_data=f'unset_main_plan_{user_id}_{course_code}_{plan_id}'))
                    else:
                        plan_buttons.append(InlineKeyboardButton("⭐ انتخاب اصلی", callback_data=f'set_main_plan_{user_id}_{course_code}_{plan_id}'))
                    
                    keyboard.append(plan_buttons)
                    text += "\n"
                
                keyboard.append([InlineKeyboardButton("📤 ارسال آخرین برنامه", callback_data=f'send_latest_plan_{user_id}_{course_code}')])
            else:
                text += "📭 هنوز هیچ برنامه‌ای برای این کاربر و دوره آپلود نشده است.\n\n"
                text += "📤 برای شروع، روی 'آپلود برنامه جدید' کلیک کنید."
            
            keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data=f'user_plans_{user_id}')])
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(text, reply_markup=reply_markup)
            
        except Exception as e:
            await admin_error_handler.handle_admin_error(
                query, None, e, f"show_user_course_plan_management:{user_id}:{course_code}", query.from_user.id
            )
