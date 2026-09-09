/* Shared interface translations for Arabic, French, and English. */
(function () {
  const STORAGE_KEY = "efa_language";
  const languages = {
    ar: { label: "العربية", dir: "rtl" },
    fr: { label: "Français", dir: "ltr" },
    en: { label: "English", dir: "ltr" },
  };
  const translations = {
    "البطولات": { fr: "Tournois", en: "Tournaments" },
    "بطولات": { fr: "Tournois", en: "Tournaments" },
    "مفتوحة للتسجيل": { fr: "ouvertes aux inscriptions", en: "open for registration" },
    "الآن": { fr: "maintenant", en: "now" },
    "لوحتي": { fr: "Mon tableau", en: "Dashboard" },
    "التصنيف": { fr: "Classement", en: "Leaderboard" },
    "المجتمع": { fr: "Communauté", en: "Community" },
    "حسابي": { fr: "Mon compte", en: "My account" },
    "خروج": { fr: "Déconnexion", en: "Log out" },
    "دخول / تسجيل": { fr: "Connexion / Inscription", en: "Log in / Sign up" },
    "فتح قائمة التنقل": { fr: "Ouvrir le menu", en: "Open navigation menu" },
    "إغلاق قائمة التنقل": { fr: "Fermer le menu", en: "Close navigation menu" },
    "تسجيل الدخول": { fr: "Connexion", en: "Log in" },
    "إنشاء حساب": { fr: "Créer un compte", en: "Create account" },
    "دخول": { fr: "Connexion", en: "Log in" },
    "حساب جديد": { fr: "Nouveau compte", en: "New account" },
    "البريد الإلكتروني": { fr: "Adresse e-mail", en: "Email address" },
    "كلمة المرور": { fr: "Mot de passe", en: "Password" },
    "كلمة المرور (8 خانات على الأقل)": { fr: "Mot de passe (8 caractères minimum)", en: "Password (at least 8 characters)" },
    "اسم اللاعب (الظاهر للجميع)": { fr: "Nom du joueur (public)", en: "Player name (public)" },
    "دخول الملعب ⚽": { fr: "Entrer dans l'arène ⚽", en: "Enter the arena ⚽" },
    "إنشاء الحساب والمشاركة 🏆": { fr: "Créer un compte et jouer 🏆", en: "Create account and play 🏆" },
    "جارٍ الدخول...": { fr: "Connexion...", en: "Signing in..." },
    "جارٍ إنشاء الحساب...": { fr: "Création du compte...", en: "Creating account..." },
    "لوحة اللاعب": { fr: "Tableau du joueur", en: "Player dashboard" },
    "تحديث البيانات ↻": { fr: "Actualiser les données ↻", en: "Refresh data ↻" },
    "الخطوة التالية": { fr: "Prochaine étape", en: "Next step" },
    "جاهز للمنافسة؟": { fr: "Prêt à jouer ?", en: "Ready to compete?" },
    "استعرض البطولات": { fr: "Voir les tournois", en: "Browse tournaments" },
    "تقييم ELO": { fr: "Classement ELO", en: "ELO rating" },
    "درجة الثقة": { fr: "Score de confiance", en: "Trust score" },
    "منصة مجانية بالكامل": { fr: "Plateforme 100 % gratuite", en: "100% free platform" },
    "مباريات فوز / خسارة": { fr: "Victoires / défaites", en: "Wins / losses" },
    "بطولاتي القادمة والجارية": { fr: "Mes tournois à venir et en cours", en: "My upcoming and active tournaments" },
    "أعلى 5 لاعبين في التصنيف": { fr: "Top 5 du classement", en: "Top 5 leaderboard players" },
    "التسجيل مفتوح": { fr: "Inscriptions ouvertes", en: "Registration open" },
    "التسجيل مغلق": { fr: "Inscriptions fermées", en: "Registration closed" },
    "جارية": { fr: "En cours", en: "In progress" },
    "منتهية": { fr: "Terminée", en: "Completed" },
    "ملغاة": { fr: "Annulée", en: "Cancelled" },
    "مسودة": { fr: "Brouillon", en: "Draft" },
    "مجانية": { fr: "Gratuit", en: "Free" },
    "موثوق": { fr: "Fiable", en: "Trusted" },
    "مقبول": { fr: "Acceptable", en: "Acceptable" },
    "تحت المراقبة": { fr: "Sous surveillance", en: "Under review" },
    "لوحة اللاعب — eFootball Arena": { fr: "Tableau du joueur — eFootball Arena", en: "Player dashboard — eFootball Arena" },
    "الدخول — eFootball Arena": { fr: "Connexion — eFootball Arena", en: "Log in — eFootball Arena" },
    "بطاقة دخول الملعب": { fr: "Carte d'accès à l'arène", en: "Arena access card" },
    "خيارات الحساب": { fr: "Options du compte", en: "Account options" },
    "ليس لديك حساب؟ افتح تبويب «حساب جديد»": { fr: "Vous n'avez pas de compte ? Ouvrez l'onglet « Nouveau compte »", en: "Don't have an account? Open the “New account” tab" },
    "سيبدأ تقييمك معنا من 1000 نقطة ELO": { fr: "Votre classement commencera à 1000 points ELO", en: "Your rating starts at 1000 ELO points" },
    "البطولات — eFootball Arena": { fr: "Tournois — eFootball Arena", en: "Tournaments — eFootball Arena" },
    "التصنيف — eFootball Arena": { fr: "Classement — eFootball Arena", en: "Leaderboard — eFootball Arena" },
    "المجتمع — eFootball Arena": { fr: "Communauté — eFootball Arena", en: "Community — eFootball Arena" },
    "eFootball Arena — منصة المنافسة الأولى": { fr: "eFootball Arena — La plateforme compétitive", en: "eFootball Arena — The competitive platform" },
    "المنظومة": { fr: "La plateforme", en: "Platform" },
    "نظام الثقة": { fr: "Système de confiance", en: "Trust system" },
    "ابدأ الآن": { fr: "Commencer", en: "Get started" },
    "انضم مجانًا": { fr: "Rejoindre gratuitement", en: "Join for free" },
    "الموسم الصفري — التسجيل مفتوح الآن": { fr: "Saison zéro — Inscriptions ouvertes", en: "Season zero — Registration open" },
    "اللعبة تكفي؟": { fr: "Le jeu suffit-il ?", en: "Is the game enough?" },
    "منافسة حقيقية": { fr: "Une vraie compétition", en: "Real competition" },
    "تحتاج منصة حقيقية.": { fr: "mérite une vraie plateforme.", en: "needs a real platform." },
    "بطولات رسمية مجانية، توثيق لنتائج المباريات، وترتيب ELO عالمي — كل ما يحتاجه لاعب eFootball الطموح في مكان واحد.": {
      fr: "Des tournois officiels gratuits, la vérification des résultats et un classement ELO mondial — tout ce dont un joueur eFootball ambitieux a besoin, au même endroit.",
      en: "Free official tournaments, verified match results, and a global ELO leaderboard — everything an ambitious eFootball player needs in one place.",
    },
    "ابدأ مسيرتك التنافسية ←": { fr: "Commencez votre parcours compétitif ←", en: "Start your competitive journey ←" },
    "اكتشف المنظومة": { fr: "Découvrir la plateforme", en: "Explore the platform" },
    "مباشرة الآن": { fr: "En direct", en: "Live now" },
    "كأس الأبطال · نصف النهائي": { fr: "Coupe des champions · Demi-finale", en: "Champions Cup · Semifinal" },
    "الدقيقة 78": { fr: "78e minute", en: "78th minute" },
    "توثيق تلقائي للنتيجة": { fr: "Vérification automatique du résultat", en: "Automatic result verification" },
    "لاعب مسجل": { fr: "Joueurs inscrits", en: "Registered players" },
    "بطولة مكتملة": { fr: "Tournois terminés", en: "Completed tournaments" },
    "مباراة موثقة": { fr: "Matchs vérifiés", en: "Verified matches" },
    "نسبة عدالة النتائج %": { fr: "Taux d'équité des résultats %", en: "Result fairness rate %" },
    "منظومة كاملة،": { fr: "Une plateforme complète,", en: "A complete platform," },
    "وليس مجرد قائمة نتائج": { fr: "pas une simple liste de résultats", en: "not just a results list" },
    "كل مكونات المنصة صُممت لهدف واحد: احترام وقت اللاعب وعدالة المنافسة.": {
      fr: "Chaque élément est conçu pour respecter le temps du joueur et garantir une compétition équitable.",
      en: "Every part is designed to respect players' time and keep competition fair.",
    },
    "بطولات بثلاث صيغ": { fr: "Tournois en trois formats", en: "Three tournament formats" },
    "خروج المغلوب، الدوري الكامل، أو نظام المجموعات + الأدوار الإقصائية — بقسمة فرق بأسلوب الأفعى حسب تقييم اللاعبين لضمان توازن المجموعات.": {
      fr: "Élimination directe, championnat ou groupes + phase finale — répartition en serpent selon le classement pour équilibrer les groupes.",
      en: "Knockout, league, or groups + playoffs — snake seeding by player rating keeps groups balanced.",
    },
    "مضاد للتلاعب": { fr: "Anti-triche", en: "Anti-cheat" },
    "توثيق النتائج": { fr: "Vérification des résultats", en: "Result verification" },
    "رفع لقطة شاشة من المباراة + تأكيد الطرفين المتبادل، وفي حال الخلاف — نظام نزاعات يحسمها بقرار الإدارة مع عقوبات على النتائج الزائفة.": {
      fr: "Téléchargez une capture du match et obtenez la confirmation des deux joueurs. En cas de désaccord, un système de litiges intervient.",
      en: "Upload a match screenshot and get confirmation from both players. If there is a dispute, the dispute system resolves it.",
    },
    "ترتيب ELO ديناميكي": { fr: "Classement ELO dynamique", en: "Dynamic ELO ranking" },
    "نظام تقييم رياضي مثبت يحسب قوة كل لاعب بعد كل مباراة، مع ترتيب موسمي يُصفَّر ويتجدد مع كل موسم جديد.": {
      fr: "Un système sportif éprouvé calcule la force de chaque joueur après chaque match, avec un classement renouvelé à chaque saison.",
      en: "A proven rating system calculates player strength after every match, with a fresh seasonal leaderboard.",
    },
    "محرك الثقة والاحتيال": { fr: "Moteur de confiance et anti-fraude", en: "Trust and fraud engine" },
    "درجة ثقة لكل لاعب تبدأ من 100، تتراجع مع البلاغات غير المبررة والتلاعب، وتتعافى تدريجيًا بالمباريات النظيفة.": {
      fr: "Un score de confiance sur 100 diminue en cas de signalements ou de triche et remonte avec des matchs propres.",
      en: "A trust score out of 100 drops with reports or cheating and recovers through clean matches.",
    },
    "منافسة مجانية بالكامل": { fr: "Compétition 100 % gratuite", en: "100% free competition" },
    "لا رسوم دخول، ولا إيداعات، ولا سحوبات. نافس من أجل التصنيف، الثقة، والإنجازات التنافسية دون حواجز مالية.": {
      fr: "Aucun frais d'inscription, dépôt ou retrait. Rivalisez pour le classement, la confiance et les succès, sans barrière financière.",
      en: "No entry fees, deposits, or withdrawals. Compete for ranking, trust, and achievements with no financial barriers.",
    },
    "مجتمع اللاعبين": { fr: "Communauté des joueurs", en: "Player community" },
    "منشورات، متابعة، وتفاعل مع أبرز اللحظات — إبقَ على اطلاع بإنجازات منافسيك وشارك أهدافك الأسطورية.": {
      fr: "Publications, abonnements et échanges autour des meilleurs moments — suivez vos rivaux et partagez vos exploits.",
      en: "Posts, follows, and reactions to the best moments — follow rivals and share your legendary plays.",
    },
    "بطولات مفتوحة للتسجيل": { fr: "Tournois ouverts aux inscriptions", en: "Tournaments open for registration" },
    "بطولات مفتوحة للتسجيل الآن": { fr: "Tournois ouverts aux inscriptions maintenant", en: "Tournaments open for registration now" },
    "اختر بطولتك المجانية، انضم، وانتظر القرعة — الطريق إلى اللقب يبدأ من هنا.": {
      fr: "Choisissez votre tournoi gratuit, rejoignez-le et attendez le tirage — le chemin vers le titre commence ici.",
      en: "Choose your free tournament, join, and await the draw — the road to the title starts here.",
    },
    "جارية الآن — دور المجموعات": { fr: "En cours — phase de groupes", en: "Live now — group stage" },
    "التسجيل مفتوح": { fr: "Inscriptions ouvertes", en: "Registration open" },
    "كأس الأبطال — موسم 1": { fr: "Coupe des champions — Saison 1", en: "Champions Cup — Season 1" },
    "دوري الأسبوع السريع": { fr: "Ligue express de la semaine", en: "Quick weekly league" },
    "تحدي الخروج المفرد": { fr: "Défi à élimination directe", en: "Single-elimination challenge" },
    "مكافأة: ELO": { fr: "Récompense : ELO", en: "Reward: ELO" },
    "٣٢ لاعبًا": { fr: "32 joueurs", en: "32 players" },
    "٣٢ لاعب": { fr: "32 joueurs", en: "32 players" },
    "👥 32 لاعبًا": { fr: "👥 32 joueurs", en: "👥 32 players" },
    "👥 16 لاعبًا": { fr: "👥 16 joueurs", en: "👥 16 players" },
    "👥 64 لاعبًا": { fr: "👥 64 joueurs", en: "👥 64 players" },
    "📅 مجموعات + إقصائي": { fr: "📅 Groupes + élimination", en: "📅 Groups + knockout" },
    "📅 دوري من دور واحد": { fr: "📅 Championnat simple", en: "📅 Single round-robin" },
    "📅 خروج المغلوب": { fr: "📅 Élimination directe", en: "📅 Knockout" },
    "خروج المغلوب": { fr: "Élimination directe", en: "Knockout" },
    "تفاصيل البطولة": { fr: "Détails du tournoi", en: "Tournament details" },
    "سجّل الآن": { fr: "S'inscrire", en: "Register now" },
    "عدالة النتائج هي": { fr: "L'équité des résultats est", en: "Result fairness is" },
    "خط الدفاع الأول": { fr: "la première ligne de défense", en: "the first line of defense" },
    "كل مباراة تمر عبر ثلاث طبقات حماية: تأكيد الطرفين، أدلة بصرية، ومحرك كشف التلاعب الذي يرصد أنماط التفادي بين حسابات مترابطة — حتى يبقى اللقب لمن يستحقه فعلًا.": {
      fr: "Chaque match passe par trois couches de protection : confirmation des deux joueurs, preuves visuelles et détection des comportements suspects.",
      en: "Every match passes through three layers of protection: both-player confirmation, visual evidence, and suspicious-pattern detection.",
    },
    "اقرأ سياسة اللعب النظيف": { fr: "Lire la politique de fair-play", en: "Read the fair-play policy" },
    "تجاوز إلى المحتوى": { fr: "Passer au contenu", en: "Skip to content" },
    "استعد. القرعة تقترب.": { fr: "Préparez-vous. Le tirage approche.", en: "Get ready. The draw is near." },
    "أنشئ حسابك الآن": { fr: "Créez votre compte", en: "Create your account" },
    "أنشئ حسابك خلال دقيقة واحدة واحصل على تقييم ELO الافتتاحي قبل انطلاق الموسم الأول.": {
      fr: "Créez votre compte en une minute et recevez votre classement ELO initial avant le début de la première saison.",
      en: "Create your account in one minute and get your starting ELO rating before the first season begins.",
    },
    "تعرّف على المنظومة": { fr: "Découvrir la plateforme", en: "Learn about the platform" },
    "اقتصاد": { fr: "Compétition gratuite", en: "Free competition" },
    "منصة تنافسية اجتماعية للاعبي eFootball — بطولات · ترتيب · توثيق · مجتمع · اقتصاد": {
      fr: "Plateforme compétitive sociale pour les joueurs eFootball — tournois · classement · vérification · communauté · compétition gratuite",
      en: "A competitive social platform for eFootball players — tournaments · rankings · verification · community · free competition",
    },
    "جميع المباريات": { fr: "Tous les matchs", en: "All matches" },
    "مجموعات + إقصائي": { fr: "Groupes + élimination", en: "Groups + knockout" },
    "دوري من دور واحد": { fr: "Championnat simple", en: "Single round-robin" },
    "النظام": { fr: "Format", en: "Format" },
    "عدد المشاركين": { fr: "Nombre de participants", en: "Participants" },
    "إلغاء": { fr: "Annuler", en: "Cancel" },
    "التفاصيل": { fr: "Détails", en: "Details" },
    "تحديث": { fr: "Actualiser", en: "Refresh" },
    "آخر التحديثات": { fr: "Dernières mises à jour", en: "Latest updates" },
    "إضافة صورة": { fr: "Ajouter une image", en: "Add image" },
    "محتوى المنشور": { fr: "Contenu de la publication", en: "Post content" },
    "اكتشف نتائج اللاعبين، احتفل بالانتصارات، وابنِ سمعتك داخل الساحة.": {
      fr: "Découvrez les résultats, célébrez les victoires et bâtissez votre réputation dans l'arène.",
      en: "Discover player results, celebrate wins, and build your reputation in the arena.",
    },
    "لا توجد تحديثات بعد. كن أول من يشارك إنجازه.": { fr: "Aucune mise à jour. Soyez le premier à partager.", en: "No updates yet. Be the first to share." },
    "جارٍ تحميل التعليقات...": { fr: "Chargement des commentaires...", en: "Loading comments..." },
    "تعذر إضافة التعليق.": { fr: "Impossible d'ajouter le commentaire.", en: "Could not add comment." },
    "تعذر نشر التحديث.": { fr: "Impossible de publier la mise à jour.", en: "Could not publish update." },
    "بحث عن لاعب": { fr: "Rechercher un joueur", en: "Search for a player" },
    "اكتب اسم اللاعب…": { fr: "Saisissez le nom du joueur…", en: "Type a player name…" },
    "لا توجد نتائج مطابقة.": { fr: "Aucun résultat correspondant.", en: "No matching results." },
    "لا يوجد مشاركون بعد.": { fr: "Aucun participant pour le moment.", en: "No participants yet." },
    "المجموعات": { fr: "Groupes", en: "Groups" },
    "الترتيب": { fr: "Classement", en: "Standings" },
    "ملف اللاعب": { fr: "Profil du joueur", en: "Player profile" },
    "المباريات": { fr: "Matchs", en: "Matches" },
    "السجل": { fr: "Bilan", en: "Record" },
    "الثقة": { fr: "Confiance", en: "Trust" },
    "تفاصيل المباراة": { fr: "Détails du match", en: "Match details" },
    "نتيجة اللاعب الأول": { fr: "Score du premier joueur", en: "First player's score" },
    "الصيغ المدعومة: JPG وPNG، والحد الأقصى 8MB.": { fr: "Formats acceptés : JPG et PNG, 8 Mo maximum.", en: "Supported formats: JPG and PNG, 8MB maximum." },
    "تأكيد النتيجة": { fr: "Confirmer le résultat", en: "Confirm result" },
    "فتح نزاع": { fr: "Ouvrir un litige", en: "Open dispute" },
    "إرسال النزاع": { fr: "Envoyer le litige", en: "Submit dispute" },
    "اللغة": { fr: "Langue", en: "Language" },
    "البطولات المفتوحة": { fr: "Tournois ouverts", en: "Open tournaments" },
    "العربية": { fr: "العربية", en: "Arabic" },
    "الفرنسية": { fr: "Français", en: "French" },
    "الإنجليزية": { fr: "English", en: "English" },
    "لا يوجد لاعبون مصنفون بعد": { fr: "Aucun joueur classé pour le moment", en: "No ranked players yet" },
    "لا توجد بيانات": { fr: "Aucune donnée", en: "No data available" },
    "تعذر الاتصال بالخادم. تأكد من تشغيل Docker (localhost:8000).": {
      fr: "Impossible de joindre le serveur. Vérifiez que Docker fonctionne (localhost:8000).",
      en: "Could not reach the server. Make sure Docker is running (localhost:8000).",
    },
    "انتهت مهلة الاتصال بالخادم. حاول مرة أخرى.": {
      fr: "La connexion a expiré. Réessayez.",
      en: "The connection timed out. Please try again.",
    },
  };

  const reverse = {};
  Object.keys(translations).forEach((source) => {
    Object.keys(translations[source]).forEach((language) => {
      reverse[translations[source][language]] = source;
    });
  });

  function currentLanguage() {
    const stored = localStorage.getItem(STORAGE_KEY);
    return languages[stored] ? stored : "ar";
  }

  function sourceText(value) {
    return reverse[value] || value;
  }

  function translate(value, language) {
    const source = sourceText(value);
    if (language === "ar") return source;
    if (translations[source] && translations[source][language]) return translations[source][language];
    return Object.keys(translations)
      .filter((key) => key.length >= 5 && source.includes(key))
      .sort((a, b) => b.length - a.length)
      .reduce((result, key) => result.split(key).join(translations[key][language] || key), source);
  }

  function apply(language = currentLanguage()) {
    document.documentElement.lang = language;
    document.documentElement.dir = languages[language].dir;
    document.title = translate(document.title, language);
    document.querySelectorAll("[data-i18n]").forEach((node) => {
      node.textContent = translate(node.dataset.i18n, language);
    });
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    let node;
    while ((node = walker.nextNode())) {
      if (!node.parentElement.closest("script, style, noscript, [data-i18n]") && node.nodeValue.trim()) {
        if (!node.__efaSource) node.__efaSource = node.nodeValue;
        const leading = node.__efaSource.match(/^\s*/)[0];
        const trailing = node.__efaSource.match(/\s*$/)[0];
        const value = node.__efaSource.trim();
        node.nodeValue = leading + translate(value, language) + trailing;
      }
    }
    document.querySelectorAll("input, textarea, [title], [aria-label]").forEach((node) => {
      ["placeholder", "title", "aria-label"].forEach((attribute) => {
        if (node.hasAttribute(attribute)) {
          const value = node.getAttribute(attribute);
          const translated = translate(value, language);
          if (translated !== value) node.setAttribute(attribute, translated);
        }
      });
    });
    document.querySelectorAll("[data-language-label]").forEach((node) => {
      node.textContent = languages[language].label;
    });
  }

  function setLanguage(language) {
    if (!languages[language]) return;
    localStorage.setItem(STORAGE_KEY, language);
    apply(language);
    document.dispatchEvent(new CustomEvent("languagechange", { detail: { language } }));
  }

  window.i18n = {
    languages,
    current: currentLanguage,
    translate,
    apply,
    setLanguage,
  };

  document.addEventListener("DOMContentLoaded", () => apply());
})();
