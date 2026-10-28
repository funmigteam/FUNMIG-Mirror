from django.conf import settings
from pathlib import Path

from django.http import Http404, HttpResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils.http import content_disposition_header

GUIDES = {
    "languages": [
        ("python", "Python", "pip, venv و PyPI"), ("javascript", "JavaScript / Node.js", "npm و مدیریت پکیج"),
        ("typescript", "TypeScript", "npm، compiler و پروژه‌ها"), ("java", "Java", "Maven و Gradle"),
        ("go", "Go", "go modules"), ("rust", "Rust", "Cargo"), ("php", "PHP", "Composer"),
        ("ruby", "Ruby", "RubyGems و Bundler"), ("csharp", "C# / .NET", "NuGet"), ("c-cpp", "C / C++", "CMake و vcpkg"),
    ],
    "systems": [
        ("linux", "Linux", "Ubuntu، Debian، Fedora و Arch"), ("windows", "Windows", "PowerShell و WSL"),
        ("macos", "macOS", "Homebrew و ابزارهای توسعه"), ("docker", "Docker", "containerهای توسعه"),
        ("android", "Android", "محیط توسعه موبایل"), ("freebsd", "FreeBSD", "ابزارهای پایه و ports"),
    ],
}

MIRRORS = [
    {"slug": "python", "name": "PyPI (pip)", "mark": "Py", "source": "Python packages", "description": "مخزن پکیج‌های Python برای نصب با pip.", "state": "active", "destination": "/pypi/"},
    {"slug": "npm", "name": "NPM", "mark": "npm", "source": "JavaScript packages", "description": "مدیر پکیج استاندارد Node.js و JavaScript.", "state": "planned"},
    {"slug": "nodejs", "name": "Node.js", "mark": "JS", "source": "Node.js runtime", "description": "runtime و ابزارهای توسعهٔ JavaScript.", "state": "planned"},
    {"slug": "docker", "name": "Docker", "mark": "DK", "source": "Container images", "description": "پلتفرم ساخت و اجرای containerهای توسعه.", "state": "planned"},
    {"slug": "composer", "name": "Composer", "mark": "C", "source": "PHP packages", "description": "مدیریت dependencyهای PHP و Packagist.", "state": "planned"},
    {"slug": "maven", "name": "Maven", "mark": "M", "source": "Java packages", "description": "ابزار build و dependency management برای Java.", "state": "planned"},
    {"slug": "gradle", "name": "Gradle", "mark": "G", "source": "Gradle plugins", "description": "ابزار build مدرن برای پروژه‌های Java و Kotlin.", "state": "planned"},
    {"slug": "go", "name": "Golang", "mark": "Go", "source": "Go modules", "description": "module proxy برای پروژه‌های Go.", "state": "planned"},
    {"slug": "cargo", "name": "Cargo", "mark": "Rs", "source": "Rust crates", "description": "مدیریت crateهای Rust و crates.io.", "state": "planned"},
    {"slug": "nuget", "name": "NuGet", "mark": ".N", "source": ".NET packages", "description": "مدیر پکیج برای C# و .NET.", "state": "planned"},
    {"slug": "yarn", "name": "Yarn", "mark": "Y", "source": "JavaScript packages", "description": "مدیر پکیج جایگزین برای JavaScript.", "state": "planned"},
    {"slug": "ubuntu", "name": "Ubuntu", "mark": "U", "source": "APT packages", "description": "پکیج‌های سیستم‌عامل Ubuntu و Debian.", "state": "planned"},
    {"slug": "alpine", "name": "Alpine", "mark": "A", "source": "APK packages", "description": "پکیج‌های سبک Alpine Linux.", "state": "planned"},
    {"slug": "fedora", "name": "Fedora", "mark": "F", "source": "DNF packages", "description": "پکیج‌های Fedora و خانوادهٔ Red Hat.", "state": "planned"},
    {"slug": "kubernetes", "name": "Kubernetes", "mark": "K8", "source": "Kubernetes packages", "description": "ابزارها و پکیج‌های موردنیاز Kubernetes.", "state": "planned"},
]

GIT_REPOSITORY_INFO = {
    "2048-master.zip": ("2048", "نسخهٔ اصلی بازی پازل عددی 2048 با HTML، CSS و JavaScript و اجرای کامل در مرورگر.", "میزبانی یک بازی پازل سبک وب"),
    "2dtanks-main.zip": ("2D Tanks", "بازی آنلاین چندنفرهٔ تانک با React، TypeScript، WebSocket و شبیه‌سازی authoritative در سرور.", "راه‌اندازی نبرد آنلاین تانک"),
    "backgammonjs-master.zip": ("Backgammon.js", "بازی تخته‌نرد چندنفره و قابل توسعه با کلاینت وب و سرور Node.js.", "میزبانی تخته‌نرد آنلاین"),
    "battleship-ai-main.zip": ("Battleship AI", "بازی جنگ دریایی مرورگری برای رقابت تک‌نفره با هوش مصنوعی هدف‌گیری.", "اجرای جنگ دریایی مقابل کامپیوتر"),
    "blockrain.js-gh-pages.zip": ("Blockrain.js", "بازی بلوک‌های سقوطی واکنش‌گرا با JavaScript و قابلیت جاسازی در صفحات وب.", "افزودن بازی آرکید به سایت"),
    "browserquest-master.zip": ("BrowserQuest", "بازی نقش‌آفرینی آنلاین چندنفرهٔ Mozilla با HTML5 Canvas، WebSocket و سرور Node.js.", "راه‌اندازی دنیای نقش‌آفرینی آنلاین"),
    "clumsy-bird-master.zip": ("Clumsy Bird", "بازی آرکید مرورگری مبتنی بر HTML5 و موتور MelonJS با سورس کامل.", "میزبانی بازی آرکید تک‌نفره"),
    "hexgl-master.zip": ("HexGL", "بازی مسابقه‌ای سه‌بعدی آینده‌نگر مبتنی بر WebGL و Three.js که مستقیماً در مرورگر اجرا می‌شود.", "میزبانی مسابقهٔ سه‌بعدی وب"),
    "hextris-gh-pages.zip": ("Hextris", "بازی پازل سریع و واکنش‌گرا با HTML5 و JavaScript برای دسکتاپ و موبایل.", "میزبانی بازی پازل مرورگری"),
    "javascript-tetris-master.zip": ("JavaScript Tetris", "پیاده‌سازی کوچک و آموزشی تتریس با JavaScript و Canvas بدون بک‌اند.", "بازی سبک و کاملاً آفلاین وب"),
    "lan-games-main.zip": ("LAN Games", "پلتفرم self-hosted شامل جنگ دریایی، ریسک، مونوپولی، چکرز و چهار بازی دیگر با Node.js، Socket.IO و SQLite.", "راه‌اندازی مجموعه بازی آنلاین در شبکه ملی"),
    "node-battleship-master.zip": ("NodeBattleship", "جنگ دریایی آنلاین دونفره با Node.js و Socket.IO، مناسب استقرار روی یک سرور داخلی.", "میزبانی جنگ دریایی آنلاین دونفره"),
    "pacman-canvas-master.zip": ("Pacman Canvas", "پیاده‌سازی متن‌باز بازی هزارتوی کلاسیک با HTML5 Canvas و بدون نیاز به بک‌اند.", "میزبانی بازی آرکید مرورگری"),
    "sandspiel-master.zip": ("Sandspiel", "شبیه‌ساز تعاملی ذرات و عناصر با Rust، WebAssembly و WebGL در مرورگر.", "راه‌اندازی بازی خلاقانهٔ شبیه‌سازی"),
    "sea-battle-v1.zip": ("Sea Battle Online", "بازی آنلاین جنگ دریایی دونفره با Express و Socket.IO و ارتباط بلادرنگ.", "نبرد دریایی آنلاین در شبکه داخلی"),
    "seabattle-multiplayer-main.zip": ("SeaBattle Multiplayer", "نسخهٔ مدرن جنگ دریایی با React، Node.js، اتاق بازی و ارتباط Socket.IO.", "راه‌اندازی جنگ دریایی اتاق‌محور"),
    "underrun-master.zip": ("UnderRun", "بازی اکشن و تیراندازی بسیار کم‌حجم که با WebGL مستقیماً در مرورگر اجرا می‌شود.", "میزبانی بازی اکشن سبک وب"),
    "zeli-web-games-main.zip": ("Zeli Web Games", "مجموعهٔ 150 مینی‌گیم مستقل React و HTML5 بدون بک‌اند یا وابستگی شبکه‌ای هنگام بازی.", "راه‌اندازی پرتال مینی‌گیم داخلی"),
    "caddy-master.zip": ("Caddy", "وب‌سرور و reverse proxy مدرن با پیکربندی ساده و پشتیبانی خودکار از HTTPS.", "میزبانی امن و پراکسی سرویس‌ها"),
    "celery-main.zip": ("Celery", "صف وظایف توزیع‌شده برای اجرای jobهای پس‌زمینه و زمان‌بندی‌شده در Python و Django.", "پردازش پس‌زمینه در پروژه‌های Python"),
    "channels-main.zip": ("Django Channels", "افزونهٔ رسمی Django برای WebSocket، long-poll و برنامه‌های ناهمزمان مبتنی بر ASGI.", "ساخت قابلیت‌های بلادرنگ در Django"),
    "compose-main.zip": ("Docker Compose", "ابزار تعریف و اجرای برنامه‌های چندکانتینری با فایل Compose.", "اجرای سرویس‌های چندکانتینری"),
    "containerd-main.zip": ("containerd", "runtime صنعتی container برای مدیریت چرخهٔ حیات image و container.", "زیرساخت اجرای containerها"),
    "daphne-main.zip": ("Daphne", "سرور HTTP، HTTP/2 و WebSocket مبتنی بر ASGI و عضو رسمی اکوسیستم Django.", "اجرای برنامه‌های ASGI و Channels"),
    "devdocs-main.zip": ("DevDocs", "مرورگر و مجموعهٔ مستندات API برای زبان‌ها و ابزارهای توسعه با قابلیت استفادهٔ آفلاین.", "مطالعهٔ آفلاین مستندات برنامه‌نویسی"),
    "llama.cpp-master.zip": ("llama.cpp", "موتور سبک C/C++ برای اجرای محلی مدل‌های زبانی و فایل‌های GGUF روی سخت‌افزارهای متنوع.", "اجرای آفلاین مدل‌های زبانی"),
    "moby-master.zip": ("Moby", "اجزای متن‌باز زیربنایی برای ساخت موتورهای container از جمله Docker Engine.", "مطالعه و توسعهٔ زیرساخت Docker"),
    "owasp-cheat-sheet-series-master.zip": ("OWASP Cheat Sheet Series", "راهنماهای عملی امنیت نرم‌افزار برای احراز هویت، API، ورودی‌ها و استقرار امن.", "مرجع امن‌سازی برنامه‌های وب"),
    "playwright-main.zip": ("Playwright", "فریم‌ورک تست end-to-end مرورگرهای Chromium، Firefox و WebKit با API یکپارچه.", "تست خودکار رابط و برنامه‌های وب"),
    "pnpm-main.zip": ("pnpm", "مدیر پکیج سریع و کم‌مصرف JavaScript با ذخیره‌سازی اشتراکی dependencyها.", "مدیریت بهینهٔ پکیج‌های JavaScript"),
    "pytest-django-main.zip": ("pytest-django", "افزونهٔ pytest برای تست پروژه‌ها و برنامه‌های Django با دسترسی کنترل‌شده به دیتابیس.", "تست خودکار پروژه‌های Django"),
    "pytest-main.zip": ("pytest", "فریم‌ورک تست ساده و توسعه‌پذیر Python با fixtureها و اکوسیستم افزونه‌ای گسترده.", "نوشتن و اجرای تست‌های Python"),
    "transformers-main.zip": ("Transformers", "کتابخانهٔ Hugging Face برای استفاده و آموزش مدل‌های زبانی، بینایی و چندوجهی.", "توسعهٔ برنامه‌های هوش مصنوعی"),
    "typescript-main.zip": ("TypeScript", "زبان توسعه‌یافتهٔ JavaScript با type checking ایستا و ابزارهای کامپایل و تحلیل کد.", "ساخت برنامه‌های JavaScript قابل نگهداری"),
    "uv-main.zip": ("uv", "مدیر بسیار سریع پکیج، محیط مجازی و پروژه‌های Python نوشته‌شده با Rust.", "مدیریت محیط و dependencyهای Python"),
    "vite-main.zip": ("Vite", "ابزار build مدرن فرانت‌اند با dev server سریع و پشتیبانی از فریم‌ورک‌های مختلف.", "ساخت و توسعهٔ سریع رابط وب"),
    "angular-main.zip": ("Angular", "پلتفرم جامع TypeScript برای ساخت برنامه‌های وب بزرگ، ساخت‌یافته و قابل نگهداری.", "توسعهٔ وب‌اپ‌های سازمانی"),
    "ansible-devel.zip": ("Ansible", "ابزار متن‌باز خودکارسازی پیکربندی، استقرار نرم‌افزار و مدیریت سرورها.", "مدیریت و خودکارسازی زیرساخت"),
    "appwrite-1.9.x.zip": ("Appwrite", "بک‌اند متن‌باز آماده برای احراز هویت، دیتابیس، ذخیره‌سازی فایل و API اپلیکیشن‌ها.", "ساخت سریع بک‌اند وب و موبایل"),
    "aspnetcore-main.zip": ("ASP.NET Core", "فریم‌ورک چندسکویی و متن‌باز مایکروسافت برای ساخت وب‌اپ، API و سرویس‌های ابری با .NET.", "توسعهٔ وب و API با دات‌نت"),
    "awesome-css-master.zip": ("Awesome CSS", "فهرست گلچین‌شده‌ای از ابزارها، فریم‌ورک‌ها، منابع و تکنیک‌های CSS.", "یافتن منابع و ابزارهای طراحی رابط"),
    "awesome-main.zip": ("Awesome", "مجموعهٔ اصلی فهرست‌های Awesome برای پیدا کردن منابع معتبر حوزه‌های مختلف نرم‌افزار.", "مرجع جامع منابع توسعه‌دهندگان"),
    "awesome-python-master.zip": ("Awesome Python", "فهرست کتابخانه‌ها، فریم‌ورک‌ها و ابزارهای پرکاربرد اکوسیستم Python.", "انتخاب ابزار مناسب پروژه‌های پایتون"),
    "awesome-selfhosted-master.zip": ("Awesome Self-Hosted", "فهرست گلچین‌شدهٔ سرویس‌ها و برنامه‌های متن‌باز قابل میزبانی روی سرور شخصی.", "انتخاب نرم‌افزارهای self-hosted"),
    "bootstrap-main.zip": ("Bootstrap", "فریم‌ورک رابط کاربری واکنش‌گرا با کامپوننت‌ها و ابزارهای CSS و JavaScript.", "ساخت سریع رابط وب واکنش‌گرا"),
    "build-your-own-x-master.zip": ("Build Your Own X", "مجموعه آموزش‌های پروژه‌محور برای ساخت ابزارهایی مانند دیتابیس، سیستم‌عامل، Git و موتور بازی از صفر.", "یادگیری عمیق با پیاده‌سازی عملی"),
    "bun-main.zip": ("Bun", "runtime و مجموعه‌ابزار سریع JavaScript و TypeScript شامل package manager، bundler و test runner.", "اجرای پروژه‌های JavaScript و TypeScript"),
    "cookiecutter-django-main.zip": ("Cookiecutter Django", "قالب استاندارد و production-ready برای شروع پروژه‌های حرفه‌ای Django.", "ساخت اسکلت امن پروژه Django"),
    "cpython-main.zip": ("CPython", "سورس پیاده‌سازی مرجع زبان Python و کتابخانهٔ استاندارد آن.", "مطالعه، توسعه و کامپایل Python"),
    "DirectX-Graphics-Samples-master.zip": ("DirectX Graphics Samples", "نمونه‌کدهای رسمی گرافیک DirectX برای Windows و GPU.", "یادگیری و آزمایش DirectX"),
    "django-main.zip": ("Django", "سورس فریم‌ورک وب سطح‌بالای Python برای توسعهٔ سریع و امن.", "ساخت بک‌اند و وب‌اپ پایتونی"),
    "django-rest-framework-main.zip": ("Django REST Framework", "ابزار قدرتمند ساخت Web API روی Django با serialization و authentication.", "ساخت REST API با Django"),
    "deno-main.zip": ("Deno", "runtime امن و مدرن JavaScript و TypeScript با ابزارهای توسعهٔ داخلی.", "اجرای سرویس‌ها و اسکریپت‌های TypeScript"),
    "docker-cli-master.zip": ("Docker CLI", "سورس ابزار خط فرمان Docker برای ساخت و مدیریت containerها، imageها و شبکه‌ها.", "مدیریت Docker از خط فرمان"),
    "fastapi-master.zip": ("FastAPI", "فریم‌ورک سریع Python برای APIهای مدرن مبتنی بر type hint و OpenAPI.", "ساخت API سریع و مستند"),
    "express-master.zip": ("Express", "فریم‌ورک مینیمال و پرکاربرد Node.js برای ساخت وب‌سرور و API.", "ساخت سرویس‌های وب با Node.js"),
    "flutter-master.zip": ("Flutter", "فریم‌ورک چندسکویی Google برای ساخت اپلیکیشن موبایل، وب و دسکتاپ با Dart.", "توسعهٔ اپلیکیشن چندسکویی"),
    "freeCodeCamp-main.zip": ("freeCodeCamp", "پلتفرم و محتوای متن‌باز آموزش برنامه‌نویسی همراه با تمرین‌ها و پروژه‌های عملی.", "یادگیری مرحله‌به‌مرحلهٔ برنامه‌نویسی"),
    "free-programming-books-main.zip": ("Free Programming Books", "فهرست بزرگ و چندزبانهٔ کتاب‌ها، دوره‌ها و منابع رایگان برنامه‌نویسی.", "پیدا کردن منابع آموزشی رایگان"),
    "grafana-main.zip": ("Grafana", "پلتفرم مصورسازی، پایش و تحلیل داده‌های عملیاتی از منابع گوناگون.", "ساخت داشبورد مانیتورینگ"),
    "gitea-main.zip": ("Gitea", "سرویس سبک و self-hosted برای میزبانی Git، issue، pull request و CI/CD.", "راه‌اندازی Git server داخلی"),
    "git-master.zip": ("Git", "سورس سیستم کنترل نسخهٔ توزیع‌شدهٔ Git همراه با مستندات و ابزارهای آن.", "مطالعه و توسعهٔ ابزار کنترل نسخه"),
    "go-master.zip": ("Go", "سورس زبان برنامه‌نویسی Go، کتابخانهٔ استاندارد و ابزارهای رسمی آن.", "توسعه و کامپایل برنامه‌های Go"),
    "gradle-9_njuy9rB.4.1-all.zip": ("Gradle 9.4.1", "توزیع کامل ابزار build گرادل همراه با مستندات و سورس‌ها.", "Build آفلاین پروژه‌های Java و Kotlin"),
    "helm-main.zip": ("Helm", "مدیر پکیج Kubernetes برای تعریف، نصب و ارتقای برنامه‌ها با Chart.", "مدیریت استقرارهای Kubernetes"),
    "immich-main.zip": ("Immich", "سامانهٔ self-hosted مدیریت و پشتیبان‌گیری عکس و ویدئو با اپلیکیشن موبایل و رابط وب.", "ساخت فضای ابری شخصی عکس و ویدئو"),
    "invidious-master.zip": ("Invidious", "فرانت‌اند متن‌باز و سبک برای مشاهدهٔ محتوای YouTube با تمرکز بر حریم خصوصی.", "راه‌اندازی رابط جایگزین YouTube"),
    "kiwix-tools-main.zip": ("Kiwix Tools", "ابزارهای خط فرمان و سرور برای ارائهٔ محتوای آفلاین با فرمت ZIM.", "میزبانی دانشنامه و مستندات آفلاین"),
    "kubernetes-master.zip": ("Kubernetes", "پلتفرم متن‌باز ارکستراسیون containerها برای استقرار و مدیریت سرویس‌های مقیاس‌پذیر.", "مدیریت خوشه‌ها و سرویس‌های کانتینری"),
    "laravel-framework-13.x.zip": ("Laravel Framework", "فریم‌ورک مدرن PHP برای ساخت برنامه‌های وب، API و سرویس‌های بک‌اند.", "توسعهٔ وب و API با PHP"),
    "mdn-content-main.zip": ("MDN Web Docs Content", "محتوای مرجع و آموزشی MDN برای HTML، CSS، JavaScript و APIهای استاندارد وب.", "دسترسی آفلاین به مستندات توسعهٔ وب"),
    "msys2-installer-main.zip": ("MSYS2 Installer", "سورس نصب‌کنندهٔ محیط MSYS2 و ابزارهای Unix-like برای Windows.", "ساخت و بررسی نصب‌کننده MSYS2"),
    "n8n-master.zip": ("n8n", "پلتفرم خودکارسازی گردش‌کار با اتصال سرویس‌ها، APIها و اجرای منطق سفارشی.", "ساخت اتوماسیون و گردش‌کار داخلی"),
    "netbox-main.zip": ("NetBox", "سامانهٔ مدیریت زیرساخت شبکه، IPAM و DCIM به‌عنوان منبع حقیقت شبکه.", "مستندسازی دیتاسنتر و شبکه"),
    "nest-master.zip": ("NestJS", "فریم‌ورک ساخت‌یافتهٔ Node.js و TypeScript برای سرویس‌های سمت سرور مقیاس‌پذیر.", "ساخت بک‌اند سازمان‌یافته با TypeScript"),
    "neovim-master.zip": ("Neovim", "ویرایشگر متن توسعه‌پذیر و مدرن سازگار با Vim با پشتیبانی از Lua و افزونه‌ها.", "ویرایش و توسعهٔ کد در ترمینال"),
    "nginx-master.zip": ("Nginx", "سورس وب‌سرور و reverse proxy سبک و پربازده Nginx.", "میزبانی وب و پراکسی سرویس‌ها"),
    "next.js-canary.zip": ("Next.js", "سورس شاخهٔ Canary فریم‌ورک React برای وب‌اپ‌های full-stack و SSR.", "توسعهٔ برنامه‌های React سمت سرور"),
    "node-main.zip": ("Node.js", "سورس runtime جاوااسکریپت سمت سرور مبتنی بر موتور V8.", "ساخت و توسعه runtime و ابزارهای Node"),
    "ogl-master.zip": ("OGL", "کتابخانهٔ سبک WebGL برای رندر گرافیک سه‌بعدی و دوبعدی در مرورگر.", "ساخت تجربه‌های گرافیکی تحت وب"),
    "ollama-main.zip": ("Ollama", "ابزار اجرای محلی مدل‌های زبانی و مدیریت مدل‌ها از طریق CLI و API.", "اجرای هوش مصنوعی روی سیستم محلی"),
    "open-webui-main.zip": ("Open WebUI", "رابط وب self-hosted برای کار با Ollama و مدل‌های هوش مصنوعی سازگار.", "رابط چت داخلی برای مدل‌های محلی"),
    "opentofu-main.zip": ("OpenTofu", "ابزار متن‌باز Infrastructure as Code برای تعریف و مدیریت منابع زیرساختی.", "مدیریت نسخه‌پذیر زیرساخت"),
    "postgres-master.zip": ("PostgreSQL", "سورس دیتابیس رابطه‌ای پیشرفته و متن‌باز PostgreSQL.", "ساخت و مطالعهٔ پایگاه‌دادهٔ رابطه‌ای"),
    "powershell-master.zip": ("PowerShell", "پوسته و زبان اسکریپت‌نویسی چندسکویی برای مدیریت سیستم و خودکارسازی.", "مدیریت Windows و Linux با اسکریپت"),
    "prometheus-main.zip": ("Prometheus", "سامانهٔ متن‌باز جمع‌آوری metrics، پایش سرویس‌ها و ایجاد هشدار.", "مانیتورینگ سرورها و برنامه‌ها"),
    "public-apis-master.zip": ("Public APIs", "فهرست دسته‌بندی‌شدهٔ APIهای عمومی برای تمرین، نمونه‌سازی و توسعهٔ نرم‌افزار.", "پیدا کردن API برای پروژه‌ها"),
    "react-main.zip": ("React", "سورس کتابخانهٔ ساخت رابط کاربری مبتنی بر component برای وب و اپلیکیشن.", "توسعه رابط‌های کاربری تعاملی"),
    "redis-unstable.zip": ("Redis", "دیتابیس سریع درون‌حافظه‌ای برای cache، صف، session و ساختارهای داده.", "پیاده‌سازی cache و پردازش سریع داده"),
    "requests-main.zip": ("Requests", "کتابخانهٔ ساده و محبوب Python برای ارسال درخواست‌های HTTP.", "ارتباط با APIها در Python"),
    "runtime-main.zip": (".NET Runtime", "سورس runtime، garbage collector و کتابخانه‌های پایهٔ پلتفرم .NET.", "مطالعه و ساخت runtime دات‌نت"),
    "rust-main.zip": ("Rust", "سورس زبان Rust، compiler و کتابخانهٔ استاندارد با تمرکز بر کارایی و ایمنی حافظه.", "توسعهٔ نرم‌افزارهای سیستمی امن"),
    "spring-framework-main.zip": ("Spring Framework", "فریم‌ورک جامع Java برای ساخت سرویس‌ها و برنامه‌های سازمانی.", "توسعه بک‌اند Java و Spring"),
    "spring-boot-main.zip": ("Spring Boot", "ابزار ساخت سریع برنامه‌ها و سرویس‌های مستقل مبتنی بر اکوسیستم Spring.", "راه‌اندازی سریع بک‌اند Java"),
    "system-design-primer-master.zip": ("System Design Primer", "راهنمای جامع طراحی سیستم‌های مقیاس‌پذیر همراه با مفاهیم، مثال‌ها و پرسش‌های مصاحبه.", "یادگیری طراحی و معماری سیستم"),
    "tailwindcss-main.zip": ("Tailwind CSS", "فریم‌ورک utility-first برای طراحی سریع رابط کاربری سفارشی.", "طراحی UI بدون CSS پراکنده"),
    "tldr-main.zip": ("TLDR Pages", "مجموعه راهنماهای کوتاه و مثال‌محور برای فرمان‌های خط فرمان در سیستم‌عامل‌های مختلف.", "یادگیری سریع دستورات ترمینال"),
    "vcredist-master.zip": ("VC Redistributable", "ابزارها و اسکریپت‌های مرتبط با بسته‌های اجرایی Microsoft Visual C++.", "آماده‌سازی وابستگی‌های اجرایی Windows"),
    "vue-core-main.zip": ("Vue.js", "هستهٔ فریم‌ورک پیش‌روندهٔ Vue برای ساخت رابط‌های کاربری و برنامه‌های تک‌صفحه‌ای.", "توسعهٔ رابط وب با Vue"),
    "vscode-main.zip": ("Visual Studio Code", "سورس ویرایشگر کد چندسکویی Visual Studio Code و زیرساخت افزونه‌های آن.", "مطالعه و توسعهٔ ویرایشگر کد"),
    "winsdk-10-master.zip": ("Windows SDK 10", "منابع و اسکریپت‌های مرتبط با Windows SDK برای توسعهٔ نرم‌افزار ویندوز.", "ساخت برنامه‌های بومی Windows"),
    "You-Dont-Know-JS-2nd-ed.zip": ("You Don't Know JS", "مجموعه‌کتاب متن‌باز برای درک عمیق سازوکارها و مفاهیم JavaScript.", "یادگیری عمیق JavaScript"),
}

def _human_size(size):
    value = float(size)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if value < 1024 or unit == "TB":
            return f"{value:.1f} {unit}" if unit != "B" else f"{int(value)} B"
        value /= 1024

def _git_repositories():
    root = settings.GIT_REPOSITORY_ROOT
    repositories = []
    if not root.is_dir():
        return repositories
    for archive in sorted(root.glob("*.zip"), key=lambda item: item.name.casefold()):
        title, description, use_case = GIT_REPOSITORY_INFO.get(
            archive.name,
            (archive.stem.replace("-", " ").title(), "آرشیو محلی یک مخزن GitHub برای استفاده و بررسی آفلاین.", "دسترسی آفلاین به سورس پروژه"),
        )
        repositories.append({"filename": archive.name, "title": title, "description": description, "use_case": use_case, "size": _human_size(archive.stat().st_size), "download_url": reverse("git-repository-download", args=[archive.name])})
    return repositories

def git_repositories(request):
    repositories = _git_repositories()
    return render(request, "core/git_repositories.html", {"repositories": repositories, "total": len(repositories)})

def git_repository_download(request, filename):
    if Path(filename).name != filename or not filename.lower().endswith(".zip"):
        raise Http404
    root = settings.GIT_REPOSITORY_ROOT.resolve()
    archive = (root / filename).resolve()
    if archive.parent != root or not archive.is_file():
        raise Http404
    response = HttpResponse(content_type="application/zip")
    response["Content-Disposition"] = content_disposition_header(True, filename)
    response["Content-Length"] = archive.stat().st_size
    response["X-Accel-Redirect"] = f"/_git_repositories/{filename}"
    return response

def home(request):
    return render(request, "core/home.html", {"domain": settings.MIRROR_DOMAIN})

def guides(request):
    return render(request, "core/guides.html", {"guides": GUIDES})

def mirrors(request):
    return render(request, "core/mirrors.html", {"mirrors": MIRRORS})

def mirror_detail(request, slug):
    item = next((mirror for mirror in MIRRORS if mirror["slug"] == slug), None)
    if not item:
        from django.http import Http404
        raise Http404
    instruction = None
    if item["slug"] == "python":
        instruction = {
            "install": "pip install --index-url https://%s/pypi/simple/ django" % settings.MIRROR_DOMAIN,
            "global": "pip config set global.index-url https://%s/pypi/simple/\npip config set global.trusted-host %s" % (settings.MIRROR_DOMAIN, settings.MIRROR_DOMAIN),
        }
    return render(request, "core/mirror_detail.html", {"mirror": item, "instruction": instruction, "mirrors": MIRRORS})

def guide(request, category, slug):
    options = dict((key, values) for key, values in GUIDES.items()).get(category, [])
    item = next((entry for entry in options if entry[0] == slug), None)
    if not item:
        from django.http import Http404
        raise Http404
    content = {
        "python": ("python3 -m venv .venv\nsource .venv/bin/activate\npip install requests", "یک درخواست HTTP با requests اجرا کنید."),
        "javascript": ("mkdir my-app && cd my-app\nnpm init -y\nnpm install lodash", "یک پروژه Node بسازید و lodash را import کنید."),
        "typescript": ("npm init -y\nnpm install -D typescript\nnpx tsc --init", "یک فایل app.ts بسازید و سپس npx tsc را اجرا کنید."),
        "java": ("mkdir hello-java && cd hello-java\njava --version\nیک فایل Hello.java بسازید", "فایل Hello.java را با javac Hello.java کامپایل و با java Hello اجرا کنید."),
        "go": ("mkdir hello-go && cd hello-go\ngo mod init example/hello\ngo run .", "در main.go یک تابع main با fmt.Println بنویسید."),
        "rust": ("cargo new hello-rust\ncd hello-rust\ncargo run", "متن پیش‌فرض Hello, world! را با cargo run اجرا کنید."),
        "php": ("mkdir hello-php && cd hello-php\ncomposer init\nphp -v", "در index.php عبارت echo 'Hello'; را بنویسید و php index.php را اجرا کنید."),
        "ruby": ("mkdir hello-ruby && cd hello-ruby\nruby -v\nbundle init", "در app.rb عبارت puts 'Hello' را بنویسید و ruby app.rb را اجرا کنید."),
        "csharp": ("dotnet new console -o hello-dotnet\ncd hello-dotnet\ndotnet run", "پروژهٔ Console ساخته‌شده را با dotnet run اجرا کنید."),
        "c-cpp": ("mkdir hello-cpp && cd hello-cpp\ncmake --version\nفایل main.cpp بسازید", "main.cpp را با g++ main.cpp -o hello و سپس ./hello اجرا کنید."),
        "linux": ("sudo apt update\nsudo apt install python3 python3-venv", "یک virtual environment با python3 -m venv .venv ایجاد کنید."),
        "windows": ("winget install Python.Python.3.13\npy -m venv .venv\n.venv\\Scripts\\activate", "پس از فعال‌سازی محیط، py -m pip install requests را اجرا کنید."),
        "macos": ("brew install python\npython3 -m venv .venv\nsource .venv/bin/activate", "پس از فعال‌سازی، pip install requests را اجرا کنید."),
        "docker": ("docker run --rm hello-world\ndocker --version", "یک Dockerfile بسازید و با docker build -t my-app . آن را build کنید."),
        "android": ("Android Studio را نصب کنید\nNew Project > Empty Activity", "یک پروژه Empty Activity بسازید و آن را روی emulator اجرا کنید."),
        "freebsd": ("pkg update\npkg install python", "با python3 -m venv .venv یک محیط مجازی ایجاد کنید."),
    }
    command, example = content[slug]
    mirror = None
    if slug == "python":
        mirror = {"title": "نصب پکیج در نت ملی", "text": "اگر پکیج از قبل در Funmig Mirror کش شده باشد، این دستور بدون اینترنت خارجی نصب را انجام می‌دهد. در حالت online، اولین نصب آن را cache می‌کند.", "command": "pip install --index-url https://%s/pypi/simple/ requests\nیا تنظیم دائمی:\npip config set global.index-url https://%s/pypi/simple/" % (settings.MIRROR_DOMAIN, settings.MIRROR_DOMAIN)}
    elif slug in {"javascript", "typescript"}:
        mirror = {"title": "وضعیت نصب پکیج در نت ملی", "text": "میرور npm هنوز فعال نشده است. پس فعلاً npm install در حالت قطع اینترنت خارجی پشتیبانی نمی‌شود؛ پس از تکمیل، دستور registry محلی همین‌جا نمایش داده خواهد شد.", "command": "npm mirror هنوز فعال نشده است"}
    return render(request, "core/guide.html", {"category": category, "slug": slug, "title": item[1], "description": item[2], "command": command, "example": example, "mirror": mirror})
