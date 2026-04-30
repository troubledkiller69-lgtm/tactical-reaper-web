const nodemailer = require('nodemailer');

module.exports = async (req, res) => {
    if (req.method !== 'POST') return res.status(405).json({ error: 'Method not allowed' });

    const { target, subject, message, amount, smtp } = req.body;

    if (!target || !smtp || !smtp.user || !smtp.pass) {
        return res.status(400).json({ error: 'MISSING_REQUIRED_PARAMS' });
    }

    const transporter = nodemailer.createTransport({
        host: smtp.host || 'smtp.gmail.com',
        port: smtp.port || 587,
        secure: smtp.port == 465,
        auth: {
            user: smtp.user,
            pass: smtp.pass
        }
    });

    const displayNames = [
        "Account Services", "Notification Center", "Support Team",
        "Customer Care", "Info Desk", "Service Alerts",
        "Security Team", "System Admin", "Priority Mail"
    ];

    const count = Math.min(amount || 1, 50); // Cap at 50 per request
    const results = { sent: 0, failed: 0, errors: [] };

    const sendEmail = async (i) => {
        const randomName = displayNames[Math.floor(Math.random() * displayNames.length)];
        const mailOptions = {
            from: `"${randomName}" <${smtp.user}>`,
            to: target,
            subject: subject || `Urgent Notification #${Math.floor(Math.random() * 100000)}`,
            text: message || `This is a tactical notification. Sequence ID: ${Math.random().toString(36).substring(7)}`,
        };

        try {
            await transporter.sendMail(mailOptions);
            results.sent++;
        } catch (error) {
            results.failed++;
            results.errors.push(error.message);
        }
    };

    // Parallel sending
    const promises = Array.from({ length: count }, (_, i) => sendEmail(i));
    await Promise.all(promises);

    res.status(200).json(results);
};
