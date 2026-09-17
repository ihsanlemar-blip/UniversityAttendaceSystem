export type SupportedLocale = 'en' | 'fa-AF' | 'ps';
export type TextDirection = 'ltr' | 'rtl';

export interface LocaleConfig {
  code: SupportedLocale;
  name: string;
  nativeName: string;
  direction: TextDirection;
  flag: string;
}

export const SUPPORTED_LOCALES: Record<SupportedLocale, LocaleConfig> = {
  en: {
    code: 'en',
    name: 'English',
    nativeName: 'English',
    direction: 'ltr',
    flag: 'US',
  },
  'fa-AF': {
    code: 'fa-AF',
    name: 'Dari (Afghanistan)',
    nativeName: 'دری',
    direction: 'rtl',
    flag: 'AF',
  },
  ps: {
    code: 'ps',
    name: 'Pashto',
    nativeName: 'پښتو',
    direction: 'rtl',
    flag: 'AF',
  },
};

export type TranslationKey =
  // Common
  | 'app.title'
  | 'app.subtitle'
  | 'common.loading'
  | 'common.refresh'
  | 'common.save'
  | 'common.cancel'
  | 'common.confirm'
  | 'common.done'
  | 'common.back'
  | 'common.next'
  | 'common.search'
  | 'common.filter'
  | 'common.all'
  | 'common.actions'
  | 'common.status'
  | 'common.details'
  | 'common.none'
  | 'common.utcTime'
  | 'common.campusNetwork'
  | 'common.online'
  | 'common.offline'

  // Navigation
  | 'nav.dashboard'
  | 'nav.attendanceReports'
  | 'nav.reviewConsole'
  | 'nav.deviceManagement'
  | 'nav.institutionalImports'
  | 'nav.securityRisks'
  | 'nav.attendancePolicies'
  | 'nav.todayClasses'
  | 'nav.sessionManagement'
  | 'nav.signOut'

  // Auth
  | 'auth.signIn'
  | 'auth.welcomeBack'
  | 'auth.credentialsPrompt'
  | 'auth.username'
  | 'auth.password'
  | 'auth.newPassword'
  | 'auth.confirmPassword'
  | 'auth.changePassword'
  | 'auth.passwordRequirements'
  | 'auth.signingIn'
  | 'auth.passwordChanged'

  // Academic / Institution Terms (Afghan context)
  | 'academic.university'
  | 'academic.faculty'
  | 'academic.department'
  | 'academic.semester'
  | 'academic.course'
  | 'academic.courseOffering'
  | 'academic.classOccurrence'
  | 'academic.student'
  | 'academic.lecturer'
  | 'academic.credit'

  // Attendance Statuses
  | 'attendance.present'
  | 'attendance.late'
  | 'attendance.absent'
  | 'attendance.excused'
  | 'attendance.leave'
  | 'attendance.pending'
  | 'attendance.notApplicable'

  // Checkpoints
  | 'checkpoint.start'
  | 'checkpoint.middle'
  | 'checkpoint.end'
  | 'checkpoint.open'
  | 'checkpoint.closed'

  // Lecturer Session
  | 'lecturer.todaySchedule'
  | 'lecturer.startSession'
  | 'lecturer.activeSession'
  | 'lecturer.closeSession'
  | 'lecturer.pauseSession'
  | 'lecturer.resumeSession'
  | 'lecturer.qrDisplay'
  | 'lecturer.bleAdvertising'
  | 'lecturer.liveRoster'
  | 'lecturer.manualOverride'
  | 'lecturer.viewReport'

  // Reviews & Operations
  | 'reviews.title'
  | 'reviews.correctionsQueue'
  | 'reviews.excusesQueue'
  | 'reviews.leaveQueue'
  | 'reviews.manualReviews'
  | 'reviews.approve'
  | 'reviews.reject'
  | 'reviews.override'
  | 'reviews.reversal'
  | 'reviews.timeline'
  | 'reviews.reason'
  | 'reviews.signal'

  // Student Mobile / Scanner
  | 'student.home'
  | 'student.checkIn'
  | 'student.attendanceConfirmed'
  | 'student.savedForSync'
  | 'student.reconciliationPending'
  | 'student.alreadyRecorded'
  | 'student.deviceSecurity'
  | 'student.osSecureStorage'
  | 'student.outbox'
  | 'student.history';

export type TranslationDictionary = Record<TranslationKey, string>;
