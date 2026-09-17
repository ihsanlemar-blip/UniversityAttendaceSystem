/// Afghan Dari translations dictionary for DSAS mobile client.
/// Preserves authentic Afghan academic terminology (پوهنتون، پوهنځی، څانګه، کریدت، سمستر، حاضر، ناوخته، غیرحاضر، معذور).
const Map<String, String> translationsFa = {
  // App
  'app_title': 'حاضری پوهنتون',
  'system_name': 'سیستم دیجیتالی حاضری محصلان',
  'select_language': 'انتخاب لسان',
  'close': 'بستن',
  'retry': 'تلاش مجدد',
  'cancel': 'انصراف',
  'confirm': 'تائید',
  'refresh': 'تازه کردن',

  // Statuses
  'status_present': 'حاضر',
  'status_late': 'ناوخته',
  'status_absent': 'غیرحاضر',
  'status_excused': 'معذور',
  'status_good_standing': 'وضعیت قناعت‌بخش',
  'status_warning': 'اخطاریه محرومی',
  'status_critical': 'در معرض محرومی',
  'status_not_applicable': 'غیرقابل تطبیق (بدون جلسات واجد شرایط)',

  // Academic Terminology
  'academic_university': 'پوهنتون',
  'academic_faculty': 'پوهنځی',
  'academic_department': 'څانګه / دیپارتمنت',
  'academic_credit': 'کریدت',
  'academic_semester': 'سمستر',
  'academic_morning_shift': 'تایم سهارنی',
  'academic_afternoon_shift': 'تایم بعد از ظهر',

  // Home Screen
  'student_id_prefix': 'نمبر تذکره/محصل: ',
  'standing_label': 'وضعیت حاضری',
  'attendance_rate': 'فیصدی مجموعی حاضری',
  'quick_actions': 'اقدامات سریع',
  'scan_qr_checkin': 'اسکن کیو‌آر حاضری',
  'device_trust': 'اعتبار دستگاه',
  'attendance_ledger': 'دفتر ثبت حاضری',
  'offline_sync_queue': 'صف همگام‌سازی آفلاین',
  'enrolled_courses': 'مضامین راجستر شده',
  'conducted_sessions': 'برگزار شده',
  'eligible_sessions': 'واجد شرایط',
  'view_details': 'مشاهده جزئیات',
  'connection_online': 'آنلاین',
  'connection_offline': 'حالت آفلاین',
  'connection_syncing': 'در حال همگام‌سازی...',

  // Scanner Screen
  'scanner_title': 'اسکن کیو‌آر حاضری',
  'scanner_instruction': 'کمره را به سمت پرده پروجکتور صنف بگیرید',
  'scanning_active': 'در حال اسکن کد کیو‌آر متحرک صنف...',
  'ble_detecting': 'در حال بررسی سیگنال بلوتوث (BLE) صنف...',
  'ble_verified': 'حضور بلوتوثی صنف تائید شد',
  'ble_not_found': 'سیگنال بلوتوث صنف دریافت نشد',
  'network_verified': 'شبکه محلی پوهنتون تائید شد',
  'manual_entry_toggle': 'ورود دستی توکن متحرک',
  'manual_token_label': 'توکن متحرک جلسه',
  'submit_token': 'ارسال توکن',

  // Check-In Result Cards
  'attendance_confirmed_title': 'حاضری تائید شد',
  'attendance_confirmed_subtitle':
      'حاضری شما در این جلسه در سرور مرکزی پوهنتون با موفقیت ثبت گردید.',
  'already_recorded_title': 'قبلاً ثبت گردیده است',
  'already_recorded_subtitle':
      'حاضری شما برای این جلسه قبلاً ثبت شده است. درخواست تکراری بدون جریمه نادیده گرفته شد.',
  'offline_recorded_title': 'ذخیره برای همگام‌سازی',
  'offline_recorded_subtitle':
      'حاضری به صورت رمزنگاری شده در دستگاه ثبت شد. با وصل مجدد اینترنت همگام‌سازی خواهد شد.',
  'token_expired_title': 'توکن منقضی شده است',
  'token_expired_subtitle':
      'کد نمایش داده شده تغییر کرده است. لطفاً کد جدید را از روی صفحه نمایش صنف اسکن نمائید.',
  'checkpoint_not_open_title': 'چک‌پاینت فعال نیست',
  'checkpoint_not_open_subtitle':
      'این نقطه حاضری در حال حاضر ثبت حضور را نمی‌پذیرد.',
  'session_closed_title': 'جلسه بسته شده است',
  'session_closed_subtitle':
      'زمان تعیین شده برای ثبت حاضری این ساعت درسی پایان یافته است.',
  'device_not_registered_title': 'دستگاه راجستر نشده است',
  'device_not_registered_subtitle':
      'این تیلفون به حساب شما متصل نیست. لطفاً ابتدا در بخش اعتبار دستگاه آن را راجستر کنید.',
  'ble_required_title': 'بلوتوث صنف الزامی است',
  'ble_required_subtitle':
      'سیگنال بلوتوث صنف یافت نشد. لطفاً مطمئن شوید بلوتوث روشن است و داخل صنف حضور دارید.',
  'campus_wifi_required_title': 'وای‌فای پوهنتون الزامی است',
  'campus_wifi_required_subtitle':
      'ثبت حاضری به اتصال به شبکه رسمی پوهنتون نیاز دارد.',
  'not_enrolled_title': 'شامل صنف نمی‌باشید',
  'not_enrolled_subtitle': 'شما رسماً در این صنف درسی راجستر نشده‌اید.',
  'server_unreachable_title': 'ارتباط با سرور برقرار نشد',
  'server_unreachable_subtitle':
      'امکان اتصال به سرور پوهنتون وجود ندارد. حاضری شما آفلاین ثبت شد.',

  // Device Trust
  'device_trust_title': 'اعتبار دستگاه و رمزنگاری',
  'device_registered': 'دستگاه راجستر و معتبر است',
  'device_unregistered': 'دستگاه راجستر نشده است',
  'device_fingerprint': 'اثر انگشت کلید دستگاه',
  'register_device': 'راجستر نمودن این دستگاه',
  'verify_hardware_keystore': 'امنیت ذخیره‌گاه کلید سیستم‌عامل تائید شد',
};
