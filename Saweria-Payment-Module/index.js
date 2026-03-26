require("dotenv").config();

// Force IPv4 (avoid IPv6 timeout issues di Indonesia)
const dns = require("dns");
dns.setDefaultResultOrder("ipv4first");

const { execFile } = require("child_process");
const { Telegraf, Markup, session } = require("telegraf");
const QRCode = require("qrcode");
const fs = require("fs");
const path = require("path");

// ===================== CONFIG =====================
const BOT_TOKEN       = process.env.BOT_TOKEN;
const ADMIN_CHAT_ID   = process.env.ADMIN_CHAT_ID || null;
const SAWERIA_USERNAME = process.env.SAWERIA_USERNAME || "zahwafe";
const SAWERIA_USER_ID  = process.env.SAWERIA_USER_ID  || "d8e876df-405c-4e08-9708-9808b9037ea5";
const CHECK_INTERVAL_MS = 7000;
const MAX_WAIT_MINUTES  = 15;
// ==================================================

// ===================== STARTUP VALIDATION =====================
if (!BOT_TOKEN) {
  console.error("❌ BOT_TOKEN tidak diset! Tambahkan BOT_TOKEN ke environment variables.");
  process.exit(1);
}
if (BOT_TOKEN.length < 40) {
  console.error("❌ BOT_TOKEN tidak valid! Panjang token minimal 40 karakter.");
  process.exit(1);
}
if (!process.env.SAWERIA_USERNAME) console.warn("⚠️  SAWERIA_USERNAME tidak diset, menggunakan nilai default.");
if (!process.env.SAWERIA_USER_ID)  console.warn("⚠️  SAWERIA_USER_ID tidak diset, menggunakan nilai default.");
if (!ADMIN_CHAT_ID) console.warn("⚠️  ADMIN_CHAT_ID tidak diset, notifikasi admin dinonaktifkan.");

// ===================== LOGGER =====================
const logger = {
  _ts() {
    return new Date().toLocaleString("id-ID", {
      timeZone: "Asia/Jakarta",
      year: "numeric", month: "2-digit", day: "2-digit",
      hour: "2-digit", minute: "2-digit", second: "2-digit",
    });
  },
  info(...m)    { console.log(`[${this._ts()}] ℹ️ `, ...m); },
  success(...m) { console.log(`[${this._ts()}] ✅`, ...m); },
  warn(...m)    { console.warn(`[${this._ts()}] ⚠️ `, ...m); },
  error(...m)   { console.error(`[${this._ts()}] ❌`, ...m); },
  debug(...m)   { if (process.env.DEBUG === "true") console.log(`[${this._ts()}] 🐛`, ...m); },
  memory() {
    const u = process.memoryUsage();
    const mb = (b) => Math.round(b / 1024 / 1024 * 10) / 10;
    const heap = mb(u.heapUsed);
    if (heap > 100) this.warn(`Memory tinggi: ${heap}MB heap used`);
    return { rss: mb(u.rss), heapUsed: heap, heapTotal: mb(u.heapTotal) };
  },
};

// ===================== RATE LIMITER =====================
class RateLimiter {
  constructor() {
    this.limits = new Map();
    // Bersihkan data lama setiap 5 menit
    setInterval(() => this._cleanup(), 5 * 60 * 1000);
  }
  isLimited(userId, maxPerMinute = 10) {
    const now = Date.now();
    const window = 60 * 1000;
    const key = String(userId);
    if (!this.limits.has(key)) this.limits.set(key, []);
    const timestamps = this.limits.get(key).filter(t => now - t < window);
    this.limits.set(key, timestamps);
    if (timestamps.length >= maxPerMinute) return true;
    timestamps.push(now);
    return false;
  }
  _cleanup() {
    const now = Date.now();
    for (const [key, ts] of this.limits) {
      const fresh = ts.filter(t => now - t < 60 * 1000);
      if (fresh.length === 0) this.limits.delete(key);
      else this.limits.set(key, fresh);
    }
  }
}
const rateLimiter = new RateLimiter();

// ===================== ERROR CATEGORIZER =====================
function categorizeError(err) {
  const msg = (err.message || "").toLowerCase();
  if (msg.includes("timeout") || msg.includes("etimedout")) return "TIMEOUT";
  if (msg.includes("rate limit") || msg.includes("429"))    return "RATE_LIMIT";
  if (msg.includes("network") || msg.includes("econnreset")) return "NETWORK";
  if (msg.includes("not found") || msg.includes("404"))     return "NOT_FOUND";
  if (msg.includes("forbidden") || msg.includes("403"))     return "PERMISSION";
  if (msg.includes("non-json") || msg.includes("invalid"))  return "VALIDATION";
  return "UNKNOWN";
}

function userFriendlyError(err) {
  const map = {
    TIMEOUT:     "⏳ Koneksi lambat. Silakan coba lagi.",
    RATE_LIMIT:  "⏳ Terlalu banyak permintaan. Tunggu sebentar.",
    NETWORK:     "🌐 Masalah koneksi. Silakan coba lagi.",
    NOT_FOUND:   "🔍 Data tidak ditemukan.",
    PERMISSION:  "🚫 Akses ditolak oleh server.",
    VALIDATION:  "📝 Respons tidak valid dari Saweria.",
    UNKNOWN:     "❌ Terjadi kesalahan. Silakan coba lagi.",
  };
  return map[categorizeError(err)] || map.UNKNOWN;
}

// ===================== CURL — BYPASS CLOUDFLARE =====================
// Menggunakan curl sistem (bukan axios) untuk lolos TLS fingerprinting Cloudflare.
// Header browser lengkap: sec-ch-ua, Sec-Fetch-*, Accept-Language id-ID, dll.
const CURL_HEADERS = [
  "-H", "Accept: */*",
  "-H", "Accept-Encoding: gzip, deflate, br, zstd",
  "-H", "Accept-Language: id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
  "-H", "DNT: 1",
  "-H", "Origin: https://saweria.co",
  "-H", "Priority: u=1, i",
  "-H", "Referer: https://saweria.co/",
  "-H", "Sec-Fetch-Dest: empty",
  "-H", "Sec-Fetch-Mode: cors",
  "-H", "Sec-Fetch-Site: same-site",
  "-H", 'sec-ch-ua: "Not:A-Brand";v="99", "Google Chrome";v="145", "Chromium";v="145"',
  "-H", "sec-ch-ua-mobile: ?0",
  "-H", "sec-ch-ua-platform: \"Windows\"",
  "-H", "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36",
];

function curlPost(url, body) {
  return new Promise((resolve, reject) => {
    const args = [
      "-s", "--compressed", "-m", "30",
      "-X", "POST", url,
      "-H", "Content-Type: application/json",
      ...CURL_HEADERS,
      "-d", JSON.stringify(body),
    ];
    execFile("curl", args, { maxBuffer: 1024 * 1024 }, (err, stdout) => {
      if (err) return reject(new Error(`curl error: ${err.message}`));
      try {
        resolve(JSON.parse(stdout));
      } catch (e) {
        reject(new Error(`Non-JSON response dari Saweria: ${stdout.slice(0, 200)}`));
      }
    });
  });
}

function curlGet(url) {
  return new Promise((resolve, reject) => {
    const args = [
      "-s", "--compressed", "-m", "30", url,
      ...CURL_HEADERS,
    ];
    execFile("curl", args, { maxBuffer: 2 * 1024 * 1024 }, (err, stdout) => {
      if (err) return reject(new Error(`curl error: ${err.message}`));
      try {
        resolve(JSON.parse(stdout));
      } catch (e) {
        reject(new Error(`Non-JSON response: ${stdout.slice(0, 200)}`));
      }
    });
  });
}

// ===================== RETRY =====================
async function withRetry(fn, retries = 3, delayMs = 2000) {
  for (let i = 0; i < retries; i++) {
    try {
      return await fn();
    } catch (err) {
      if (i === retries - 1) throw err;
      const wait = delayMs * Math.pow(2, i);
      logger.warn(`Retry ${i + 1}/${retries} setelah ${wait}ms: ${err.message}`);
      await new Promise((r) => setTimeout(r, wait));
    }
  }
}

// ===================== BOT =====================
const bot = new Telegraf(BOT_TOKEN, {
  telegram: { apiRoot: "https://api.telegram.org" },
});
bot.use(session());

const SAWERIA_API = "https://backend.saweria.co";

const NOMINAL_OPTIONS = [
  { label: "⚡ Rp 5.000",   value: 5000 },
  { label: "⚡ Rp 10.000",  value: 10000 },
  { label: "⚡ Rp 20.000",  value: 20000 },
  { label: "⚡ Rp 35.000",  value: 35000 },
  { label: "⚡ Rp 50.000",  value: 50000 },
  { label: "⚡ Rp 100.000", value: 100000 },
];

// ===================== SAWERIA API =====================

async function calculateAmount(amount) {
  return withRetry(async () => {
    const payload = {
      agree: true, notUnderage: true,
      message: "-", amount,
      payment_type: "qris", vote: "", giphy: null, yt: "", ytStart: 0,
      mediaType: null, image_guess: null, image_guess_answer: "",
      amountToPay: "", currency: "IDR", pgFee: "", platformFee: "",
      customer_info: { first_name: "bot", email: "bot@bot.bot", phone: "" },
    };
    const res = await curlPost(
      `${SAWERIA_API}/donations/${SAWERIA_USERNAME}/calculate_pg_amount`,
      payload
    );
    if (!res?.data?.amount_to_pay) throw new Error("calculateAmount: respons tidak valid");
    return res.data;
  });
}

async function createDonation(amount, email, name, message) {
  return withRetry(async () => {
    const payload = {
      agree: true, notUnderage: true,
      message: message || "-", amount,
      payment_type: "qris", vote: "", currency: "IDR",
      customer_info: { first_name: name, email, phone: "" },
    };
    const res = await curlPost(
      `${SAWERIA_API}/donations/snap/${SAWERIA_USER_ID}`,
      payload
    );
    if (!res?.data?.qr_string) throw new Error(res?.message || "createDonation: respons tidak valid");
    return res.data;
  });
}

async function checkPaymentStatus(donationId) {
  try {
    const res = await curlGet(`${SAWERIA_API}/donations/qris/snap/${donationId}`);
    const d = res?.data;
    if (d) return { id: d.id, status: d.transaction_status, amount: d.amount_raw, created_at: d.created_at };
    logger.warn("checkPaymentStatus: response tidak ada data:", JSON.stringify(res)?.slice(0, 200));
  } catch (e) {
    logger.warn("checkPaymentStatus error:", e.message);
  }
  return null;
}

async function generateQRImage(qrString, donationId) {
  const filePath = path.join("/tmp", `qr_${donationId}.png`);
  await QRCode.toFile(filePath, qrString, {
    width: 500, margin: 2,
    color: { dark: "#000000", light: "#ffffff" },
  });
  return filePath;
}

// ===================== ADMIN NOTIFIKASI =====================
async function notifyAdmin(bot, text) {
  if (!ADMIN_CHAT_ID) return;
  try {
    await bot.telegram.sendMessage(ADMIN_CHAT_ID, text, { parse_mode: "Markdown" });
  } catch (e) {
    logger.warn("Gagal kirim notif admin:", e.message);
  }
}

// ===================== HELPERS =====================
function formatRupiah(amount) {
  return new Intl.NumberFormat("id-ID", {
    style: "currency", currency: "IDR", minimumFractionDigits: 0,
  }).format(amount);
}

function formatCountdown(secondsLeft) {
  const m = Math.floor(secondsLeft / 60);
  const s = secondsLeft % 60;
  return `${m}:${String(s).padStart(2, "0")}`;
}

// ===================== FILE UTILS =====================
function deleteQRFile(donationId) {
  const qrFile = path.join("/tmp", `qr_${donationId}.png`);
  try { if (fs.existsSync(qrFile)) fs.unlinkSync(qrFile); } catch (_) {}
}

function stopPolling(donationId) {
  if (activeIntervals[donationId]) {
    clearInterval(activeIntervals[donationId]);
    delete activeIntervals[donationId];
  }
  deleteQRFile(donationId);
}

function stopAllPolling() {
  for (const id of Object.keys(activeIntervals)) stopPolling(id);
}

// ===================== MENU =====================
function showMainMenu(ctx, edit = false) {
  const text =
    `🏠 *Menu Utama*\n\n` +
    `Halo *${ctx.from?.first_name || "Kamu"}*! 👋\n` +
    `Selamat datang di bot donasi *${SAWERIA_USERNAME}*\n\n` +
    `Silakan pilih menu di bawah:`;
  const keyboard = Markup.inlineKeyboard([
    [Markup.button.callback("💸 Donasi Sekarang", "menu_donasi")],
    [Markup.button.callback("🔍 Cek Status Pembayaran", "menu_cek_status")],
    [Markup.button.callback("ℹ️ Tentang Bot", "menu_info")],
  ]);
  if (edit) return ctx.editMessageText(text, { parse_mode: "Markdown", ...keyboard });
  return ctx.replyWithMarkdown(text, keyboard);
}

function showNominalMenu(ctx, edit = false) {
  const buttons = NOMINAL_OPTIONS.map((opt) =>
    Markup.button.callback(opt.label, `amount_${opt.value}`)
  );
  const rows = [];
  for (let i = 0; i < buttons.length; i += 2) rows.push(buttons.slice(i, i + 2));
  rows.push([Markup.button.callback("✏️ Nominal Lain", "amount_custom")]);
  rows.push([Markup.button.callback("🔙 Kembali", "back_main")]);
  const text = `💰 *Pilih Nominal Donasi*\n\nUntuk: *${SAWERIA_USERNAME}*\nPilih nominal atau masukkan sendiri:`;
  const keyboard = Markup.inlineKeyboard(rows);
  if (edit) return ctx.editMessageText(text, { parse_mode: "Markdown", ...keyboard });
  return ctx.replyWithMarkdown(text, keyboard);
}

// ===================== POLLING =====================
const activeIntervals = {};
const processingUsers = new Set();
const BOT_START_TIME = Date.now();

// Sub-handler per status — dipecah dari pollPaymentStatus
async function onPaymentSuccess(ctx, chatId, msgId, donationId, amountRaw, name) {
  stopPolling(donationId);
  try {
    await ctx.telegram.editMessageText(
      chatId, msgId, null,
      `✅ *Pembayaran Berhasil!*\n\n` +
      `💰 Jumlah: ${formatRupiah(amountRaw)}\n` +
      `🎉 Terima kasih *${name}* sudah support *${SAWERIA_USERNAME}*!\n\n` +
      `_ID:_ \`${donationId}\``,
      {
        parse_mode: "Markdown",
        ...Markup.inlineKeyboard([
          [Markup.button.callback("💸 Donasi Lagi", "menu_donasi_new")],
          [Markup.button.callback("🏠 Menu Utama", "back_main_new")],
        ]),
      }
    );
  } catch (_) {}

  // Notifikasi admin
  await notifyAdmin(bot,
    `💳 *DONASI MASUK*\n\n` +
    `👤 Dari: *${name}*\n` +
    `💰 Jumlah: ${formatRupiah(amountRaw)}\n` +
    `🆔 Ref: \`${donationId}\``
  );
}

async function onPaymentFailed(ctx, chatId, msgId, donationId) {
  stopPolling(donationId);
  try {
    await ctx.telegram.editMessageText(
      chatId, msgId, null,
      `❌ *Pembayaran Gagal / Dibatalkan*\n\nSilakan coba donasi lagi.`,
      {
        parse_mode: "Markdown",
        ...Markup.inlineKeyboard([
          [Markup.button.callback("💸 Donasi Lagi", "menu_donasi_new")],
          [Markup.button.callback("🏠 Menu Utama", "back_main_new")],
        ]),
      }
    );
  } catch (_) {}
}

async function onPaymentExpired(ctx, chatId, msgId, donationId) {
  stopPolling(donationId);
  try {
    await ctx.telegram.editMessageText(
      chatId, msgId, null,
      `⏰ *Waktu Habis*\n\nQR sudah tidak valid (${MAX_WAIT_MINUTES} menit berlalu).\nBuat donasi baru ya!`,
      {
        parse_mode: "Markdown",
        ...Markup.inlineKeyboard([
          [Markup.button.callback("💸 Donasi Lagi", "menu_donasi_new")],
          [Markup.button.callback("🏠 Menu Utama", "back_main_new")],
        ]),
      }
    );
  } catch (_) {}
}

function pollPaymentStatus(ctx, donationId, chatId, msgId, amountRaw, name) {
  const startTime = Date.now();
  const totalMs = MAX_WAIT_MINUTES * 60 * 1000;
  let lastEditedMinute = MAX_WAIT_MINUTES;

  const interval = setInterval(async () => {
    try {
      // Date.now() — lebih akurat dari attempts * interval
      const secondsLeft = Math.max(0, Math.floor((totalMs - (Date.now() - startTime)) / 1000));
      const data = await checkPaymentStatus(donationId);
      const rawStatus = (data?.status || "").toUpperCase();

      // CAPTURE ditambahkan — status Midtrans untuk kartu kredit
      if (["SUCCESS", "SETTLEMENT", "PAID", "CAPTURE"].includes(rawStatus)) {
        await onPaymentSuccess(ctx, chatId, msgId, donationId, amountRaw, name);

      } else if (["FAILED", "EXPIRED", "CANCEL", "FAILURE", "DENY"].includes(rawStatus)) {
        await onPaymentFailed(ctx, chatId, msgId, donationId);

      } else if (secondsLeft <= 0) {
        await onPaymentExpired(ctx, chatId, msgId, donationId);

      } else {
        const currentMinute = Math.floor(secondsLeft / 60);
        if (currentMinute < lastEditedMinute) {
          lastEditedMinute = currentMinute;
          try {
            await ctx.telegram.editMessageText(
              chatId, msgId, null,
              `⏳ *Menunggu Pembayaran...*\n\n` +
              `🆔 ID: \`${donationId}\`\n` +
              `⏱ Sisa waktu: *${formatCountdown(secondsLeft)}*\n\n` +
              `_Otomatis update setelah bayar_`,
              {
                parse_mode: "Markdown",
                ...Markup.inlineKeyboard([
                  [Markup.button.callback("🔍 Cek Sekarang", `check_${donationId}`)],
                  [Markup.button.callback("❌ Batalkan", `cancel_${donationId}`)],
                ]),
              }
            );
          } catch (_) {}
        }
      }
    } catch (pollErr) {
      logger.error("Poll error pada donasi", donationId, ":", pollErr.message);
    }
  }, CHECK_INTERVAL_MS);

  return interval;
}

// ===================== BOT COMMANDS =====================

// /start
bot.start(async (ctx) => { ctx.session = {}; await showMainMenu(ctx); });

// /health — hanya admin
bot.command("health", async (ctx) => {
  const userId = String(ctx.from?.id);
  if (!ADMIN_CHAT_ID || userId !== String(ADMIN_CHAT_ID)) {
    return ctx.reply("⛔ Perintah ini hanya untuk admin.");
  }
  const mem = logger.memory();
  const uptimeMs = Date.now() - BOT_START_TIME;
  const h = Math.floor(uptimeMs / 3600000);
  const m = Math.floor((uptimeMs % 3600000) / 60000);
  const s = Math.floor((uptimeMs % 60000) / 1000);
  const activeCount = Object.keys(activeIntervals).length;

  await ctx.replyWithMarkdown(
    `🏥 *System Health*\n\n` +
    `✅ Status: RUNNING\n` +
    `⏱ Uptime: *${h}h ${m}m ${s}s*\n\n` +
    `💾 *Memory:*\n` +
    `   • Heap Used: ${mem.heapUsed} MB\n` +
    `   • Heap Total: ${mem.heapTotal} MB\n` +
    `   • RSS: ${mem.rss} MB\n\n` +
    `📊 *Polling Aktif:* ${activeCount} transaksi\n` +
    `👥 *Users Proses:* ${processingUsers.size}\n\n` +
    `_${new Date().toLocaleString("id-ID", { timeZone: "Asia/Jakarta" })}_`
  );
});

// ===================== BOT ACTIONS =====================

bot.action("back_main", async (ctx) => {
  await ctx.answerCbQuery();
  ctx.session = {};
  await showMainMenu(ctx, true);
});
bot.action("back_main_new", async (ctx) => {
  await ctx.answerCbQuery();
  ctx.session = {};
  await showMainMenu(ctx, false);
});

bot.action("menu_info", async (ctx) => {
  await ctx.answerCbQuery();
  await ctx.editMessageText(
    `ℹ️ *Tentang Bot Donasi*\n\n` +
    `🎯 Creator: [${SAWERIA_USERNAME}](https://saweria.co/${SAWERIA_USERNAME})\n` +
    `💳 Metode: QRIS (semua e-wallet & m-banking)\n` +
    `🔒 Aman via Saweria\n` +
    `⏰ Waktu bayar: *${MAX_WAIT_MINUTES} menit*`,
    {
      parse_mode: "Markdown",
      disable_web_page_preview: true,
      ...Markup.inlineKeyboard([[Markup.button.callback("🔙 Kembali", "back_main")]]),
    }
  );
});

bot.action("menu_cek_status", async (ctx) => {
  await ctx.answerCbQuery();
  ctx.session = { step: "input_cek_id" };
  await ctx.editMessageText(
    `🔍 *Cek Status Pembayaran*\n\nKetik *ID Transaksi* kamu:\n\n_Contoh:_\n\`08e1e8c5-7c85-445d-9b7b-085241d8b27c\``,
    {
      parse_mode: "Markdown",
      ...Markup.inlineKeyboard([[Markup.button.callback("🔙 Kembali", "back_main")]]),
    }
  );
});

bot.action("menu_donasi", async (ctx) => {
  await ctx.answerCbQuery();
  ctx.session = { step: "choose_amount" };
  await showNominalMenu(ctx, true);
});
bot.action("menu_donasi_new", async (ctx) => {
  await ctx.answerCbQuery();
  ctx.session = { step: "choose_amount" };
  await showNominalMenu(ctx, false);
});

bot.action(/^amount_(\d+)$/, async (ctx) => {
  const amount = parseInt(ctx.match[1]);
  ctx.session = { step: "input_name", amount };
  await ctx.answerCbQuery();
  await ctx.editMessageText(
    `✅ Nominal: *${formatRupiah(amount)}*\n\n👤 Masukkan *nama* kamu:`,
    {
      parse_mode: "Markdown",
      ...Markup.inlineKeyboard([
        [Markup.button.callback("🔙 Ganti Nominal", "menu_donasi")],
        [Markup.button.callback("🏠 Menu Utama", "back_main")],
      ]),
    }
  );
});

bot.action("amount_custom", async (ctx) => {
  ctx.session = { step: "input_custom_amount" };
  await ctx.answerCbQuery();
  await ctx.editMessageText(
    `✏️ *Masukkan Nominal*\n\nKetik jumlah donasi (angka saja, min. Rp 1.000):\n\n_Contoh:_ \`25000\``,
    {
      parse_mode: "Markdown",
      ...Markup.inlineKeyboard([[Markup.button.callback("🔙 Kembali", "menu_donasi")]]),
    }
  );
});

bot.action("skip_message", async (ctx) => {
  await ctx.answerCbQuery();
  try { await ctx.editMessageReplyMarkup({ inline_keyboard: [] }); } catch (_) {}
  await processMessage(ctx, "");
});

bot.action(/^check_(.+)$/, async (ctx) => {
  const donationId = ctx.match[1];
  const data = await checkPaymentStatus(donationId);

  if (!data) {
    return ctx.answerCbQuery("❌ Gagal cek status, coba lagi.", { show_alert: true });
  }

  const normalStatus = (data.status || "").toUpperCase();
  if (["SUCCESS", "SETTLEMENT", "PAID", "CAPTURE"].includes(normalStatus)) {
    // biarkan polling handler yang update pesan, cukup dismiss spinner
    return ctx.answerCbQuery("✅ Pembayaran terdeteksi!");
  }
  if (["FAILED", "EXPIRED", "CANCEL", "FAILURE", "DENY"].includes(normalStatus)) {
    return ctx.answerCbQuery("❌ Pembayaran gagal/dibatalkan.");
  }

  // masih pending
  return ctx.answerCbQuery("⏳ Masih menunggu pembayaran.", { show_alert: true });
});

bot.action(/^cancel_(.+)$/, async (ctx) => {
  await ctx.answerCbQuery("Transaksi dibatalkan");
  const donationId = ctx.match[1];
  stopPolling(donationId);
  try {
    await ctx.editMessageText(
      `❌ *Transaksi Dibatalkan*`,
      {
        parse_mode: "Markdown",
        ...Markup.inlineKeyboard([
          [Markup.button.callback("💸 Donasi Lagi", "menu_donasi_new")],
          [Markup.button.callback("🏠 Menu Utama", "back_main_new")],
        ]),
      }
    );
  } catch (_) {}
});

// ===================== HANDLER TEKS =====================
bot.on("text", async (ctx) => {
  try {
    const userId = ctx.from?.id;

    // Rate limiter: max 15 pesan/menit per user
    if (rateLimiter.isLimited(userId, 15)) {
      return ctx.reply("⏳ Terlalu cepat. Tunggu sebentar ya.");
    }

    const session = ctx.session || {};
    const text = ctx.message.text.trim();

    if (session.step === "input_cek_id") {
      const loadingMsg = await ctx.reply("🔍 Mengecek status...");
      const data = await checkPaymentStatus(text);
      try { await ctx.telegram.deleteMessage(ctx.chat.id, loadingMsg.message_id); } catch (_) {}

      if (!data) {
        ctx.session = {};
        return ctx.replyWithMarkdown(
          `❌ *Transaksi tidak ditemukan*\n\nPastikan ID transaksi benar.`,
          Markup.inlineKeyboard([
            [Markup.button.callback("🔍 Cek Lagi", "menu_cek_status")],
            [Markup.button.callback("🏠 Menu Utama", "back_main_new")],
          ])
        );
      }

      const normalStatus = (data.status || "").toUpperCase();
      const statusEmoji = ["SUCCESS", "SETTLEMENT", "PAID", "CAPTURE"].includes(normalStatus)
        ? "✅" : normalStatus === "PENDING" ? "⏳" : "❌";

      ctx.session = {};
      return ctx.replyWithMarkdown(
        `${statusEmoji} *Status Pembayaran*\n\n` +
        `🆔 ID: \`${data.id}\`\n` +
        `💰 Jumlah: ${formatRupiah(data.amount)}\n` +
        `📌 Status: *${data.status}*\n` +
        `📅 Tanggal: ${data.created_at}`,
        Markup.inlineKeyboard([
          [Markup.button.callback("🔍 Cek Lagi", "menu_cek_status")],
          [Markup.button.callback("🏠 Menu Utama", "back_main_new")],
        ])
      );
    }

    if (session.step === "input_custom_amount") {
      const amount = parseInt(text.replace(/\D/g, ""));
      if (isNaN(amount) || amount < 1000) {
        return ctx.reply("⚠️ Nominal tidak valid. Min Rp 1.000 (angka saja).",
          Markup.inlineKeyboard([[Markup.button.callback("🔙 Kembali", "menu_donasi_new")]])
        );
      }
      ctx.session.amount = amount;
      ctx.session.step = "input_name";
      return ctx.replyWithMarkdown(
        `✅ Nominal: *${formatRupiah(amount)}*\n\n👤 Masukkan *nama* kamu:`,
        Markup.inlineKeyboard([
          [Markup.button.callback("🔙 Ganti Nominal", "menu_donasi_new")],
          [Markup.button.callback("🏠 Menu Utama", "back_main_new")],
        ])
      );
    }

    if (session.step === "input_name") {
      if (text.length < 2) return ctx.reply("⚠️ Nama minimal 2 karakter.");
      ctx.session.name = text;
      ctx.session.step = "input_email";
      return ctx.replyWithMarkdown(
        `👤 Nama: *${text}*\n\n📧 Masukkan *email* kamu:`,
        Markup.inlineKeyboard([
          [Markup.button.callback("🔙 Ganti Nominal", "menu_donasi_new")],
          [Markup.button.callback("🏠 Menu Utama", "back_main_new")],
        ])
      );
    }

    if (session.step === "input_email") {
      if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(text)) {
        return ctx.reply("⚠️ Format email tidak valid. Coba lagi:");
      }
      ctx.session.email = text;
      ctx.session.step = "input_message";
      return ctx.replyWithMarkdown(
        `📧 Email: *${text}*\n\n💬 Tulis *pesan* untuk *${SAWERIA_USERNAME}*:`,
        Markup.inlineKeyboard([
          [Markup.button.callback("⏭ Skip Pesan", "skip_message")],
          [Markup.button.callback("🏠 Menu Utama", "back_main_new")],
        ])
      );
    }

    if (session.step === "input_message") {
      await processMessage(ctx, text === "-" ? "" : text);
    }
  } catch (err) {
    logger.error("bot.on text error:", err.message);
    try { await ctx.reply("⚠️ Terjadi kesalahan. Kirim /start untuk mulai ulang."); } catch (_) {}
  }
});

// Global error handler — tangkap semua unhandled rejection dari action handlers
bot.catch((err, ctx) => {
  logger.error(`bot.catch [${ctx.updateType}]:`, err.message);
  ctx.reply(userFriendlyError(err)).catch(() => {});
});

// ===================== PROSES DONASI =====================
async function processMessage(ctx, message) {
  const userId = ctx.from?.id;
  if (processingUsers.has(userId)) {
    return ctx.reply("⚠️ Donasi sedang diproses, tunggu sebentar ya.");
  }
  processingUsers.add(userId);
  const autoCleanup = setTimeout(() => processingUsers.delete(userId), 5 * 60 * 1000);

  ctx.session.step = "processing";
  const { amount, name, email } = ctx.session;
  const chatId = ctx.chat.id;

  const processingMsg = await ctx.replyWithMarkdown(
    `⏳ *Memproses donasi...*\n💰 ${formatRupiah(amount)} untuk *${SAWERIA_USERNAME}*`
  );

  try {
    // calculateAmount — tanpa checkEligible (tidak diperlukan)
    const calcData = await calculateAmount(amount);
    const { amount_to_pay, pg_fee } = calcData;

    const donation = await createDonation(amount, email, name, message);
    const { qr_string: qrString, id: donationId } = donation;
    const qrPath = await generateQRImage(qrString, donationId);

    try { await ctx.telegram.deleteMessage(chatId, processingMsg.message_id); } catch (_) {}

    await ctx.replyWithPhoto(
      { source: qrPath },
      {
        caption:
          `🧾 *Detail Donasi*\n\n` +
          `👤 Nama: *${name}*\n` +
          `💰 Nominal: ${formatRupiah(amount)}\n` +
          `💳 Biaya PG: ${formatRupiah(pg_fee)}\n` +
          `💵 *Total Bayar: ${formatRupiah(amount_to_pay)}*\n` +
          `💬 Pesan: ${message || "-"}\n\n` +
          `📱 *Scan QR pakai e-wallet / m-banking*\n` +
          `⏰ Waktu bayar: *${MAX_WAIT_MINUTES} menit*`,
        parse_mode: "Markdown",
      }
    );

    const statusMsg = await ctx.replyWithMarkdown(
      `⏳ *Menunggu Pembayaran...*\n\n` +
      `🆔 ID: \`${donationId}\`\n` +
      `⏱ Sisa waktu: *${MAX_WAIT_MINUTES}:00*\n\n` +
      `_Otomatis update setelah bayar_`,
      Markup.inlineKeyboard([
        [Markup.button.callback("🔍 Cek Sekarang", `check_${donationId}`)],
        [Markup.button.callback("❌ Batalkan", `cancel_${donationId}`)],
      ])
    );

    const intervalId = pollPaymentStatus(ctx, donationId, chatId, statusMsg.message_id, amount_to_pay, name);
    activeIntervals[donationId] = intervalId;

    clearTimeout(autoCleanup);
    processingUsers.delete(userId);
    ctx.session = {};
    logger.info(`Donasi dimulai: user=${userId}, nominal=${amount}, id=${donationId}`);

  } catch (err) {
    clearTimeout(autoCleanup);
    processingUsers.delete(userId);
    ctx.session = {};

    const errMsg = userFriendlyError(err);
    logger.error("processMessage error:", err.message);

    // Safety net: kalau pesan processing masih ada, edit. Kalau tidak, reply baru.
    try {
      await ctx.telegram.editMessageText(
        chatId, processingMsg.message_id, null,
        `❌ *Gagal Membuat Donasi*\n\n${errMsg}`,
        {
          parse_mode: "Markdown",
          ...Markup.inlineKeyboard([
            [Markup.button.callback("🔄 Coba Lagi", "menu_donasi_new")],
            [Markup.button.callback("🏠 Menu Utama", "back_main_new")],
          ]),
        }
      );
    } catch (_) {
      // Kalau edit gagal, kirim pesan baru
      await ctx.reply(`❌ *Gagal Membuat Donasi*\n\n${errMsg}`, {
        parse_mode: "Markdown",
        ...Markup.inlineKeyboard([
          [Markup.button.callback("🔄 Coba Lagi", "menu_donasi_new")],
        ]),
      }).catch(() => {});
    }

    // Alert admin jika ada error saat proses donasi
    await notifyAdmin(bot,
      `🚨 *ERROR DONASI*\n\n` +
      `👤 User: ${name} (${userId})\n` +
      `💰 Nominal: ${formatRupiah(amount)}\n` +
      `❌ Error: ${err.message}`
    );
  }
}

// ===================== START =====================
function gracefulShutdown(signal) {
  logger.info(`${signal} diterima, membersihkan dan mematikan bot...`);
  stopAllPolling();
  bot.stop(signal);
}

process.once("SIGINT",  () => gracefulShutdown("SIGINT"));
process.once("SIGTERM", () => gracefulShutdown("SIGTERM"));

logger.info("🤖 Bot Saweria dimulai...");
bot.launch({
  polling: { timeout: 30, limit: 100 },
}).then(() => logger.success("Bot berjalan! Kirim /start ke bot kamu."))
  .catch((err) => {
    logger.error("Gagal start bot:", err.message);
    process.exit(1);
  });
