/// Pashto translations dictionary for DSAS mobile client.
/// Preserves authentic Afghan academic terminology (پوهنتون، پوهنځی، څانګه، کریدت، سمستر، حاضر، ناوخته، غیرحاضر، معذور).
const Map<String, String> translationsPs = {
  // App
  'app_title': 'د پوهنتون حاضري',
  'system_name': 'د محصلینو د حاضرۍ ډیجیټلي سیسټم',
  'select_language': 'ژبه وټاکئ',
  'close': 'بندول',
  'retry': 'بیا هڅه',
  'cancel': 'لغوه کول',
  'confirm': 'تائید',
  'refresh': 'تازه کول',

  // Statuses
  'status_present': 'حاضر',
  'status_late': 'ناوخته',
  'status_absent': 'غیرحاضر',
  'status_excused': 'معذور',
  'status_good_standing': 'قناعت بخښونکی حالت',
  'status_warning': 'د محرومۍ خبرداری',
  'status_critical': 'د محرومۍ خطر',
  'status_not_applicable': 'د تطبیق وړ نه دی (د شرایطو وړ ناستې نشته)',

  // Academic Terminology
  'academic_university': 'پوهنتون',
  'academic_faculty': 'پوهنځی',
  'academic_department': 'څانګه',
  'academic_credit': 'کریدت',
  'academic_semester': 'سمستر',
  'academic_morning_shift': 'سهارنی تایم',
  'academic_afternoon_shift': 'ماسپښین تایم',

  // Home Screen
  'student_id_prefix': 'د محصل شمېره: ',
  'standing_label': 'د حاضرۍ حالت',
  'attendance_rate': 'د حاضرۍ ټولیزه سلنه',
  'quick_actions': 'چټک ګامونه',
  'scan_qr_checkin': 'د حاضرۍ کیو‌آر سکن',
  'device_trust': 'د آلې باور',
  'attendance_ledger': 'د حاضرۍ کتابچه',
  'offline_sync_queue': 'آفلاین همغږۍ قطار',
  'enrolled_courses': 'راجستر شوي مضامین',
  'conducted_sessions': 'ترسره شوې',
  'eligible_sessions': 'د شرایطو وړ',
  'view_details': 'تفصیلات کتل',
  'connection_online': 'آنلاین',
  'connection_offline': 'آفلاین حالت',
  'connection_syncing': 'د همغږۍ په حال کې...',

  // Scanner Screen
  'scanner_title': 'د حاضرۍ کیو‌آر سکن',
  'scanner_instruction': 'کیمره د ټولګي پروجکټور پردې ته مخامخ ونیسئ',
  'scanning_active': 'د ټولګي خوځنده کیو‌آر کوډ د سکن کېدو په حال کې...',
  'ble_detecting': 'د ټولګي د بلوتوث (BLE) شتون څېړل کیږي...',
  'ble_verified': 'د ټولګي بلوتوث شتون تائید شو',
  'ble_not_found': 'د ټولګي بلوتوث سګنل ونه موندل شو',
  'network_verified': 'د پوهنتون ځایی شبکه تائید شوه',
  'manual_entry_toggle': 'د متحرک ټوکن لاسي لیکل',
  'manual_token_label': 'د ناستې متحرک ټوکن',
  'submit_token': 'ټوکن ثبت کړئ',

  // Check-In Result Cards
  'attendance_confirmed_title': 'حاضري تائید شوه',
  'attendance_confirmed_subtitle':
      'ستاسو حاضري د پوهنتون په مرکزي سرور کې په بریالیتوب سره ثبته شوه.',
  'already_recorded_title': 'مخکې ثبته شوې ده',
  'already_recorded_subtitle':
      'ستاسو حاضري د دې ناستې لپاره مخکې ثبت شوې وه. تکراري غوښتنه له جزا پرته رد شوه.',
  'offline_recorded_title': 'د همغږۍ لپاره خوندي شو',
  'offline_recorded_subtitle':
      'حاضري په کوډ شوې بڼه په آله کې ثبته شوه. د انټرنیټ له نښلېدو سره به واستول شي.',
  'token_expired_title': 'ټوکن ختم شوی دی',
  'token_expired_subtitle':
      'ښودل شوی کوډ بدل شوی دی. مهرباني وکړئ نوی کوډ د ټولګي له پردې سکن کړئ.',
  'checkpoint_not_open_title': 'د حاضرۍ نقطه پرانیستې نه ده',
  'checkpoint_not_open_subtitle': 'دا نقطه اوس مهال حاضري نه مني.',
  'session_closed_title': 'ناسته پای ته ورسېده',
  'session_closed_subtitle':
      'د دې درسي ساعت لپاره د حاضرۍ ټاکلی وخت پای ته رسېدلی دی.',
  'device_not_registered_title': 'آله نه ده ثبت شوې',
  'device_not_registered_subtitle':
      'دا تلیفون ستاسو له حساب سره نه دی نښلول شوی. لومړی یې د آلې باور برخه کې ثبت کړئ.',
  'ble_required_title': 'د ټولګي بلوتوث اړین دی',
  'ble_required_subtitle':
      'د ټولګي بلوتوث سګنل ونه موندل شو. ډاډ ترلاسه کړئ چې بلوتوث روښانه دی او ټولګي کې یاست.',
  'campus_wifi_required_title': 'د پوهنتون وای‌فای اړین دی',
  'campus_wifi_required_subtitle':
      'د حاضرۍ ثبت د پوهنتون له رسمي شبکې سره نښلېدو ته اړتیا لري.',
  'not_enrolled_title': 'ټولګي کې شامل نه یاست',
  'not_enrolled_subtitle':
      'تاسو په رسمي ډول په دې درسي ټولګي کې نه یاست ثبت شوي.',
  'server_unreachable_title': 'له سرور سره اړیکه ونه شوه',
  'server_unreachable_subtitle':
      'د پوهنتون له سرور سره اړیکه نشته. ستاسو حاضري آفلاین خوندي شوه.',

  // Device Trust
  'device_trust_title': 'د آلې باور او کوډګري',
  'device_registered': 'آله ثبت او باوري ده',
  'device_unregistered': 'آله نه ده ثبت شوې',
  'device_fingerprint': 'د آلې کیلي ګوتې نښه',
  'register_device': 'د دې آلې ثبت کول',
  'verify_hardware_keystore': 'د هارډویر کیلي امنیت تائید شو',
};
