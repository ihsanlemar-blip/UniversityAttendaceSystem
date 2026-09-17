import { SupportedLocale } from './types';

export interface UserSafeError {
  code: string;
  title: string;
  description: string;
}

const ERROR_DICTIONARY: Record<string, Record<SupportedLocale, { title: string; description: string }>> = {
  AUTHENTICATION_REQUIRED: {
    en: {
      title: 'Authentication Required',
      description: 'Your session has expired or you are not signed in. Please sign in to continue.',
    },
    'fa-AF': {
      title: 'ورود الزامی است',
      description: 'جلسه کاری شما پایان یافته یا وارد سیستم نشده‌اید. لطفاً وارد شوید.',
    },
    ps: {
      title: 'ننوتل اړین دي',
      description: 'ستاسو د کار وخت پای ته رسېدلی یا نه یاست داخل شوي. مهرباني وکړئ ننوځئ.',
    },
  },
  PERMISSION_DENIED: {
    en: {
      title: 'Access Denied (403)',
      description: 'You do not have the required institutional permissions to perform this action.',
    },
    'fa-AF': {
      title: 'دسترسی محدود است (۴۰۳)',
      description: 'حساب شما صلاحیت و مجوز اداری لازم برای این بخش را ندارد.',
    },
    ps: {
      title: 'لاسرسی رد شو (۴۰۳)',
      description: 'ستاسو کارن‌حساب د دغه کار د ترسره کولو لپاره اړین واک نه لري.',
    },
  },
  SESSION_EXPIRED: {
    en: {
      title: 'Session Expired',
      description: 'Your authentication token has expired. Please sign in again.',
    },
    'fa-AF': {
      title: 'انقضای جلسه کاری',
      description: 'توکن ورود شما منقضی گردیده است. لطفاً مجدداً وارد شوید.',
    },
    ps: {
      title: 'د کار وخت پای ته ورسېد',
      description: 'ستاسو د ننوتلو نښه پای ته رسېدلې. مهرباني وکړئ بیا ننوځئ.',
    },
  },
  TOKEN_EXPIRED: {
    en: {
      title: 'QR Code Expired',
      description: 'The rotating classroom QR code has expired. Please scan the current code displayed on the screen.',
    },
    'fa-AF': {
      title: 'کد کیوآر منقضی شد',
      description: 'کد تصویری متحرک صنف منقضی شده است. لطفاً کد جدید نمایش داده شده در پروجکتور را اسکن نمایید.',
    },
    ps: {
      title: 'کیو آر کوډ پای ته ورسېد',
      description: 'د صنف خوځنده کوډ پای ته رسېدلی. مهرباني وکړئ د پروجکټور تازه کوډ سکن کړئ.',
    },
  },
  CHECKPOINT_NOT_OPEN: {
    en: {
      title: 'Checkpoint Not Open',
      description: 'No attendance checkpoint window is currently open for this session.',
    },
    'fa-AF': {
      title: 'چک‌پاینت باز نیست',
      description: 'در حال حاضر هیچ مرحله‌ای از حاضری برای این صنف باز نمی‌باشد.',
    },
    ps: {
      title: 'چک‌پاینټ خلاص نه دی',
      description: 'اوس مهال د دې غونډې لپاره د حاضرۍ هېڅ چک‌پاینټ خلاص نه دی.',
    },
  },
  CHECKPOINT_CLOSED: {
    en: {
      title: 'Checkpoint Closed',
      description: 'The verification window for this checkpoint has closed.',
    },
    'fa-AF': {
      title: 'چک‌پاینت بسته شد',
      description: 'مهلت زمانی تأیید حضور در این مرحله به پایان رسیده است.',
    },
    ps: {
      title: 'چک‌پاینټ بند شو',
      description: 'د دې مرحلې د شتون تصدیق کولو وخت پای ته رسېدلی دی.',
    },
  },
  SESSION_CLOSED: {
    en: {
      title: 'Session Concluded',
      description: 'This attendance session has been finalized and closed by the lecturer.',
    },
    'fa-AF': {
      title: 'جلسه صنف خاتمه یافته است',
      description: 'این جلسه حاضری توسط استاد صنف نهایی و بسته شده است.',
    },
    ps: {
      title: 'د حاضرۍ غونډه پای ته رسېدلې',
      description: 'دغه غونډه د استاد لخوا بشپړه او تړل شوې ده.',
    },
  },
  NOT_ENROLLED: {
    en: {
      title: 'Not Enrolled in Course',
      description: 'Your student account is not enrolled in this course offering for the active semester.',
    },
    'fa-AF': {
      title: 'عدم شمولیت در مضمون',
      description: 'حساب شما در لست محصلان رسمی این مضمون در سمستر جاری ثبت نشده است.',
    },
    ps: {
      title: 'په مضمون کې نه یاست شامل',
      description: 'ستاسو کارن په دې سمستر کې د دغه مضمون په رسمي لست کې نه دی ثبت.',
    },
  },
  DEVICE_NOT_REGISTERED: {
    en: {
      title: 'Device Not Registered',
      description: 'This device is not activated as your primary attendance phone. Please register in Device Security.',
    },
    'fa-AF': {
      title: 'دستگاه ثبت نشده است',
      description: 'این موبایل به عنوان دستگاه اصلی شما ثبت نگردیده. لطفاً در بخش امنیت دستگاه آن را فعال کنید.',
    },
    ps: {
      title: 'وسیله نه ده ثبت شوې',
      description: 'دا ګرځنده آیفون ستاسو د اصلي وسیلې په توګه نه دی ثبت. د وسیلو په برخه کې یې فعال کړئ.',
    },
  },
  DEVICE_SUSPENDED: {
    en: {
      title: 'Device Suspended',
      description: 'Your registered device has been suspended or revoked by an administrator.',
    },
    'fa-AF': {
      title: 'دستگاه به حالت تعلیق درآمده است',
      description: 'اعتبار این دستگاه توسط اداره پوهنتون به حالت تعلیق یا لغو درآمده است.',
    },
    ps: {
      title: 'وسیله ځنډول شوې',
      description: 'ستاسو ثبت شوې وسیله د ادارې لخوا ځنډول شوې یا لغوه شوې ده.',
    },
  },
  DEVICE_REPLACED: {
    en: {
      title: 'Device Replaced',
      description: 'This device was replaced by a new primary device and is no longer authorized.',
    },
    'fa-AF': {
      title: 'دستگاه تعویض شده است',
      description: 'این دستگاه با یک موبایل جدید جایگزین شده و دیگر معتبر نمی‌باشد.',
    },
    ps: {
      title: 'وسیله بدله شوې ده',
      description: 'دا وسیله په یو نوي موبایل بدله شوې او نور د اعتبار وړ نه ده.',
    },
  },
  BLE_REQUIRED: {
    en: {
      title: 'Classroom BLE Beacon Required',
      description: 'Classroom Bluetooth beacon was not detected. Ensure Bluetooth is enabled and you are inside the classroom.',
    },
    'fa-AF': {
      title: 'سیگنال بلوتوث صنف الزامی است',
      description: 'سیگنال بلوتوث صنف دریافت نشد. مطمئن شوید بلوتوث فعال بوده و در داخل صنف حضور دارید.',
    },
    ps: {
      title: 'د ټولګي بلوتوث اړین دی',
      description: 'د ټولګي د بلوتوث سیګنال ونه موندل شو. باوري شئ چې بلوتوث فعال دی او په ټولګي کې یاست.',
    },
  },
  BLE_NOT_DETECTED: {
    en: {
      title: 'Classroom BLE Not Detected',
      description: 'Bluetooth presence beacon not detected within physical classroom range.',
    },
    'fa-AF': {
      title: 'بلوتوث صنف شناسایی نشد',
      description: 'سیگنال بلوتوث در محدوده فزیکی صنف درسی شناسایی نگردید.',
    },
    ps: {
      title: 'د ټولګي بلوتوث پیدا نشو',
      description: 'د صنف په فزیکي ساحه کې د بلوتوث نښه ونه موندل شوه.',
    },
  },
  CAMPUS_NETWORK_NOT_DETECTED: {
    en: {
      title: 'Campus Network Required',
      description: 'You must connect to the authorized university campus Wi-Fi network to complete check-in.',
    },
    'fa-AF': {
      title: 'اتصال به شبکه پوهنتون الزامی است',
      description: 'برای ثبت حضور، باید به شبکه وای‌فای رسمی و مجاز پوهنتون وصل باشید.',
    },
    ps: {
      title: 'د پوهنتون انټرنیټ ته وصل شئ',
      description: 'د شتون ثبتولو لپاره باید د پوهنتون له رسمي وای‌فای شبکې سره وصل شئ.',
    },
  },
  NETWORK_CHALLENGE_EXPIRED: {
    en: {
      title: 'Network Proof Expired',
      description: 'The campus network cryptographic challenge expired. Please retry check-in.',
    },
    'fa-AF': {
      title: 'اعتبار شبکه منقضی شد',
      description: 'اعتبارسنجی شبکه منقضی گردید. لطفاً مجدداً امتحان نمایید.',
    },
    ps: {
      title: 'د شبکې تصدیق پای ته ورسېد',
      description: 'د شبکې تصدیق پای ته ورسېد. مهرباني وکړئ بیا هڅه وکړئ.',
    },
  },
  CORRECTION_WINDOW_CLOSED: {
    en: {
      title: 'Correction Window Closed',
      description: 'The allowed deadline for submitting an attendance correction for this session has passed.',
    },
    'fa-AF': {
      title: 'مهلت تصحیح خاتمه یافته',
      description: 'فرصت قانونی ارسال درخواست تصحیح حاضری برای این جلسه به پایان رسیده است.',
    },
    ps: {
      title: 'د سمون وخت پای ته ورسېد',
      description: 'د دې غونډې لپاره د سمون غوښتنې قانوني وخت پای ته رسېدلی دی.',
    },
  },
  REQUEST_ALREADY_RESOLVED: {
    en: {
      title: 'Request Already Resolved',
      description: 'This request has already been approved or rejected by an attendance reviewer.',
    },
    'fa-AF': {
      title: 'درخواست قبلاً بررسی شده است',
      description: 'این درخواست قبلاً توسط مسؤل مربوطه تأیید یا رد گردیده است.',
    },
    ps: {
      title: 'غوښتنه مخکې ارزول شوې',
      description: 'دا غوښتنه پخوا د مسوول مدیر لخوا منل شوې یا رد شوې ده.',
    },
  },
  IMPORT_VALIDATION_ERROR: {
    en: {
      title: 'Import Validation Failed',
      description: 'Uploaded file contains structural or formatting errors. Please review the preview report.',
    },
    'fa-AF': {
      title: 'خطا در اعتبارسنجی فایل',
      description: 'فایل ارسالی دارای خطاهای ساختاری یا معلوماتی است. لطفاً گزارش پیش‌نمایش را بررسی نمایید.',
    },
    ps: {
      title: 'د فایل په واردولو کې تېروتنه',
      description: 'فایل جوړښتي یا بڼیزې تېروتنې لري. مهرباني وکړئ لومړنی راپور وګورئ.',
    },
  },
};

/**
 * Maps raw backend error codes into localized, sanitized user-facing descriptions.
 * Prevents exposure of database internals, cryptographic details, or raw stack traces.
 */
export function getLocalizedError(code: string, locale: SupportedLocale = 'en'): UserSafeError {
  const normalized = code.trim().toUpperCase();
  const entry = ERROR_DICTIONARY[normalized];
  if (entry && entry[locale]) {
    return {
      code: normalized,
      title: entry[locale].title,
      description: entry[locale].description,
    };
  }

  // Safe institutional fallbacks without leaking raw backend errors
  const fallbackTitles: Record<SupportedLocale, string> = {
    en: 'Operation Notice',
    'fa-AF': 'اطلاعیه عملیاتی',
    ps: 'عملیاتي خبرتیا',
  };

  const fallbackDescriptions: Record<SupportedLocale, string> = {
    en: 'An institutional policy or connectivity rule prevented this action. Please verify session conditions or contact administration.',
    'fa-AF': 'یک قانون سازمانی یا محدودیت ارتباطی مانع این اقدام گردید. لطفاً شرایط جلسه را بررسی کرده یا با اداره تماس بگیرید.',
    ps: 'یوې اداري تګلارې یا شبکې د دغه کار مخه ونیوله. مهرباني وکړئ د ټولګي حالت وګورئ یا له ادارې سره اړیکه ونیسئ.',
  };

  return {
    code: normalized,
    title: fallbackTitles[locale] || fallbackTitles.en,
    description: fallbackDescriptions[locale] || fallbackDescriptions.en,
  };
}
