'use client';

import React, { useState } from 'react';
import { X, Send, MessageSquareText, ShieldAlert, CheckCircle2 } from 'lucide-react';
import { sendVendorWarning } from '@/lib/api';

interface ActionItem {
  id: string;
  title: string;
  description: string;
  recommended_fix?: string;
  vendor_name?: string;
  vendor_phone?: string;
  vendor_gstin?: string;
  affected_amount: number;
}

interface VendorWarningModalProps {
  action: ActionItem | null;
  onClose: () => void;
  onSuccess: () => void;
}

export const VendorWarningModal: React.FC<VendorWarningModalProps> = ({ action, onClose, onSuccess }) => {
  if (!action) return null;

  const [channel, setChannel] = useState<'whatsapp' | 'email'>('whatsapp');
  const [phone, setPhone] = useState(action.vendor_phone || '919876543210');
  const [customMessage, setCustomMessage] = useState(
    `🙏 *Notice from CA Desk regarding GST Compliance*\n\n` +
    `Dear ${action.vendor_name || 'Vendor'},\n\n` +
    `We noticed a critical compliance issue regarding your invoice details:\n` +
    `⚠️ *${action.title}*\n` +
    `📝 ${action.description}\n\n` +
    `💡 *Action Required:* ${action.recommended_fix || 'Please review and update your filing.'}\n` +
    `💰 Affected Amount: ₹${action.affected_amount?.toLocaleString('en-IN')}\n\n` +
    `Please respond or update your GSTR-1 to ensure uninterrupted business.`
  );
  const [isSending, setIsSending] = useState(false);
  const [sentSuccess, setSentSuccess] = useState(false);

  const handleSend = async () => {
    setIsSending(true);
    try {
      await sendVendorWarning({
        action_item_id: action.id,
        channel,
        vendor_phone: phone,
        message: customMessage,
      });
      setSentSuccess(true);
      setTimeout(() => {
        onSuccess();
        onClose();
      }, 1500);
    } catch (err) {
      console.error('Failed to send vendor warning:', err);
    } finally {
      setIsSending(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-md p-4 animate-in fade-in">
      <div className="glass-panel w-full max-w-xl rounded-2xl border border-white/10 shadow-2xl p-6 relative">
        
        {/* Close Button */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-white/10 transition-all"
        >
          <X className="w-5 h-5" />
        </button>

        {sentSuccess ? (
          <div className="text-center py-12 space-y-3">
            <div className="w-14 h-14 bg-emerald-500/20 text-emerald-400 rounded-full flex items-center justify-center mx-auto glow-emerald">
              <CheckCircle2 className="w-8 h-8" />
            </div>
            <h3 className="text-lg font-bold text-white">WhatsApp Warning Sent!</h3>
            <p className="text-xs text-slate-400">
              The vendor has been notified via Meta WhatsApp Cloud API.
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            
            {/* Modal Header */}
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 rounded-xl bg-emerald-500/20 text-emerald-400 flex items-center justify-center glow-emerald">
                <MessageSquareText className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-base font-bold text-white">Send Vendor Notice</h3>
                <p className="text-xs text-slate-400">
                  Notify {action.vendor_name || 'Vendor'} directly via WhatsApp
                </p>
              </div>
            </div>

            {/* Target Channel */}
            <div className="flex items-center space-x-3 bg-slate-900/60 p-2 rounded-xl border border-white/5">
              <button
                onClick={() => setChannel('whatsapp')}
                className={`flex-1 py-1.5 rounded-lg text-xs font-semibold flex items-center justify-center space-x-2 transition-all ${
                  channel === 'whatsapp'
                    ? 'bg-emerald-500 text-slate-950 glow-emerald font-bold'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                <MessageSquareText className="w-3.5 h-3.5" />
                <span>WhatsApp Cloud API</span>
              </button>

              <button
                onClick={() => setChannel('email')}
                className={`flex-1 py-1.5 rounded-lg text-xs font-semibold flex items-center justify-center space-x-2 transition-all ${
                  channel === 'email'
                    ? 'bg-emerald-500 text-slate-950 glow-emerald font-bold'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                <span>Dedicated Email</span>
              </button>
            </div>

            {/* Phone Input */}
            <div>
              <label className="block text-[11px] font-semibold text-slate-300 mb-1">
                Vendor WhatsApp Phone Number
              </label>
              <input
                type="text"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                className="w-full bg-slate-900/80 border border-white/10 rounded-xl px-3.5 py-2 text-xs text-white focus:outline-none focus:border-emerald-500/50"
                placeholder="e.g. 919876543210"
              />
            </div>

            {/* Message Preview */}
            <div>
              <label className="block text-[11px] font-semibold text-slate-300 mb-1">
                Message Body
              </label>
              <textarea
                rows={7}
                value={customMessage}
                onChange={(e) => setCustomMessage(e.target.value)}
                className="w-full bg-slate-900/80 border border-white/10 rounded-xl p-3 text-xs text-slate-200 font-mono focus:outline-none focus:border-emerald-500/50 leading-relaxed"
              />
            </div>

            {/* Action Buttons */}
            <div className="flex items-center justify-end space-x-3 pt-2">
              <button
                onClick={onClose}
                className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-400 hover:text-white hover:bg-white/5 transition-all"
              >
                Cancel
              </button>
              <button
                onClick={handleSend}
                disabled={isSending}
                className="flex items-center space-x-2 px-5 py-2 rounded-xl text-xs font-bold bg-emerald-500 hover:bg-emerald-400 text-slate-950 transition-all glow-emerald disabled:opacity-50"
              >
                <Send className="w-3.5 h-3.5" />
                <span>{isSending ? 'Dispatching...' : 'Dispatch WhatsApp Warning'}</span>
              </button>
            </div>

          </div>
        )}
      </div>
    </div>
  );
};
