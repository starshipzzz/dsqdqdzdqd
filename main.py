conv_handler = ConversationHandler(
    entry_points=[CommandHandler('start', start)],
    states={
        CHOOSE_CATEGORY: [
            CallbackQueryHandler(show_products, pattern='^category_'),
            CallbackQueryHandler(admin, pattern='^admin$'),
            CallbackQueryHandler(show_home, pattern='^back_to_home$')
        ],
        
        CHOOSING_PRODUCT: [
            CallbackQueryHandler(show_product, pattern='^product_'),
            CallbackQueryHandler(show_home, pattern='^back_to_categories$')
        ],

        WAITING_PRODUCT_NAME: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_product_name)
        ],

        WAITING_PRODUCT_DESCRIPTION: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_product_description)
        ],

        WAITING_PRODUCT_PRICE: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_product_price)
        ],

        WAITING_PRODUCT_MEDIA: [
            MessageHandler(filters.PHOTO | filters.VIDEO, handle_product_media),
            CallbackQueryHandler(finish_adding_media, pattern='^finish_media$'),
            CallbackQueryHandler(cancel_add_product, pattern='^cancel_add_product$')
        ],

        WAITING_PRODUCT_CATEGORY: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_product_category),
            CallbackQueryHandler(handle_product_category_button, pattern='^select_category_')
        ],

        CONFIRM_ADD_PRODUCT: [
            CallbackQueryHandler(confirm_add_product, pattern='^confirm_add_product$'),
            CallbackQueryHandler(cancel_add_product, pattern='^cancel_add_product$')
        ],

        CHOOSING_PRODUCT_TO_REMOVE: [
            CallbackQueryHandler(confirm_remove_product, pattern='^remove_product_'),
            CallbackQueryHandler(admin, pattern='^back_to_admin$')
        ],

        CHOOSING_PRODUCT_TO_EDIT: [
            CallbackQueryHandler(edit_product_menu, pattern='^edit_product_'),
            CallbackQueryHandler(admin, pattern='^back_to_admin$')
        ],

        EDITING_PRODUCT: [
            CallbackQueryHandler(start_edit_name, pattern='^edit_name$'),
            CallbackQueryHandler(start_edit_description, pattern='^edit_description$'),
            CallbackQueryHandler(start_edit_price, pattern='^edit_price$'),
            CallbackQueryHandler(start_edit_media, pattern='^edit_media$'),
            CallbackQueryHandler(start_edit_category, pattern='^edit_category$'),
            CallbackQueryHandler(admin, pattern='^back_to_admin$')
        ],

        WAITING_NEW_NAME: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_new_name)
        ],

        WAITING_NEW_DESCRIPTION: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_new_description)
        ],

        WAITING_NEW_PRICE: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_new_price)
        ],

        WAITING_NEW_MEDIA: [
            MessageHandler(filters.PHOTO | filters.VIDEO, handle_new_media),
            CallbackQueryHandler(finish_editing_media, pattern='^finish_media$'),
            CallbackQueryHandler(edit_product_menu, pattern='^back_to_edit$')
        ],

        WAITING_NEW_CATEGORY: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_new_category),
            CallbackQueryHandler(handle_new_category_button, pattern='^select_category_')
        ],

        # Nouvel état pour le contrôle d'accès
        WAITING_ACCESS_CODE: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, access_control.verify_code)
        ],
    },
    fallbacks=[CommandHandler('cancel', cancel)]
)
