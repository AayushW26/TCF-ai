'use client';

import React, { useState } from 'react';
import { 
  MessageSquareText, 
  Send, 
  Paperclip, 
  Image as ImageIcon, 
  FileText, 
  ShieldCheck, 
  CheckCheck,
  Building2,
  Sparkles,
  Bot,
  User
} from 'lucide-react';

interface ChatMessage {
  id: string;
  sender: 'user' | 'bot';
  text?: string;
  image?: string;
  extraction?: any;
  timestamp: string;
}

export default function TraderWebAppPage() {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 'msg-1',
      sender: 'bot',
      text: '🙏 *Namaste! Welcome to Munim.ai*\n\nI\'m your GST compliance assistant. Upload a photo or PDF of your invoice and I\'ll extract the data & check your ITC eligibility instantly!',
      timestamp: '10:00 AM',
    },
  ]);

  const [inputText, setInputText] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);

  const handleSendMessage = (textToSend?: string, imageFile?: File) => {
    const content = textToSend || inputText;
    if (!content && !imageFile) return;

    const timeStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

    // User message
    const userMsg: ChatMessage = {
      id: `user-${Date.now()}`,
      sender: 'user',
      text: content,
      timestamp: timeStr,
    };

    setMessages((prev) => [...prev, userMsg]);
    setInputText('');
    setIsProcessing(true);

    // Simulate backend response
    setTimeout(() => {
      let botReply: ChatMessage;

      if (imageFile || content.toLowerCase().includes('invoice') || content.toLowerCase().includes('bill')) {
        botReply = {
          id: `bot-${Date.now()}`,
          sender: 'bot',
          text: '📥 *Invoice Received! Processing with Gemini Vision OCR...* ⏳',
          extraction: {
            supplier_name: 'Mahavir Logistics & Transport',
            supplier_gstin: '27AABCM9012K1ZX',
            invoice_number: 'INV-904',
            invoice_date: '2026-08-01',
            total_amount: 59000.0,
            itc_status: 'FRAUD_FLAGGED',
            blocked_reason: 'Fraud Score 78/100: Sequential invoice numbers detected from same supplier',
            confidence: 0.95,
          },
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        };
      } else if (content.toLowerCase().includes('status')) {
        botReply = {
          id: `bot-${Date.now()}`,
          sender: 'bot',
          text: '📊 *Account Status*\n\nBusiness: Shree Ganesh Traders\nGSTIN: 27AADCS1234M1Z5\nInvoices processed this month: 12\nConfirmed ITC: ₹3,12,000\n\n📸 Send an invoice photo to extract details!',
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        };
      } else {
        botReply = {
          id: `bot-${Date.now()}`,
          sender: 'bot',
          text: '✅ Message received! You can upload an invoice image or type:\n• *status* — check your account\n• *help* — see options',
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        };
      }

      setMessages((prev) => [...prev, botReply]);
      setIsProcessing(false);
    }, 1200);
  };

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      handleSendMessage(`[Uploaded File: ${file.name}]`, file);
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6 pb-16">
      
      {/* Header */}
      <div className="glass-panel p-6 rounded-3xl border border-white/10 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2 text-xs font-semibold text-emerald-400 mb-1">
            <MessageSquareText className="w-4 h-4" />
            <span>Trader Web App & Invoice Ingestion</span>
          </div>
          <h1 className="text-2xl font-extrabold text-white">
            WhatsApp & Direct Invoice Processing Portal
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Upload or forward invoices via WhatsApp or web to run instant Gemini multimodal extraction
          </p>
        </div>

        <div className="flex items-center space-x-2 text-xs font-medium text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-3.5 py-2 rounded-xl">
          <Sparkles className="w-4 h-4" />
          <span>Meta WhatsApp Cloud API Connected</span>
        </div>
      </div>

      {/* WhatsApp Window Wrapper */}
      <div className="glass-panel rounded-3xl border border-white/10 overflow-hidden shadow-2xl flex flex-col h-[650px] relative">
        
        {/* WhatsApp Top Header */}
        <div className="bg-slate-900/90 px-6 py-4 border-b border-white/10 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-full bg-gradient-to-tr from-emerald-500 to-sky-500 p-0.5 glow-emerald">
              <div className="w-full h-full bg-navy-900 rounded-full flex items-center justify-center">
                <Bot className="w-5 h-5 text-emerald-400" />
              </div>
            </div>
            <div>
              <div className="text-sm font-bold text-white flex items-center gap-1.5">
                Munim.ai Assistant
                <span className="w-2 h-2 rounded-full bg-emerald-400 glow-emerald" />
              </div>
              <div className="text-[10px] text-emerald-400/90 font-medium">
                Official Business Account • Online
              </div>
            </div>
          </div>

          <div className="text-xs text-slate-400 bg-white/5 px-3 py-1.5 rounded-lg border border-white/5">
            +91 98765 43210
          </div>
        </div>

        {/* Chat Messages Body */}
        <div className="flex-1 p-6 overflow-y-auto space-y-4 bg-slate-950/60 backdrop-blur-md">
          {messages.map((msg) => (
            <div
              key={msg.id}
              className={`flex items-start gap-2.5 ${msg.sender === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              {msg.sender === 'bot' && (
                <div className="w-7 h-7 rounded-full bg-emerald-500/20 text-emerald-400 flex items-center justify-center shrink-0 mt-1">
                  <Bot className="w-4 h-4" />
                </div>
              )}

              <div
                className={`max-w-md rounded-2xl p-4 text-xs leading-relaxed ${
                  msg.sender === 'user'
                    ? 'bg-emerald-600 text-white rounded-tr-none shadow-lg'
                    : 'bg-slate-900/90 text-slate-200 border border-white/10 rounded-tl-none shadow-lg'
                }`}
              >
                {msg.text && (
                  <div className="whitespace-pre-line font-sans">
                    {msg.text}
                  </div>
                )}

                {/* Extraction Card Box inside chat */}
                {msg.extraction && (
                  <div className="mt-3 bg-slate-950/80 p-3 rounded-xl border border-white/10 space-y-2 text-[11px]">
                    <div className="font-bold text-emerald-400 border-b border-white/10 pb-1 flex items-center justify-between">
                      <span>📋 Extracted Data (Gemini 2.5)</span>
                      <span>{(msg.extraction.confidence * 100).toFixed(0)}% Match</span>
                    </div>
                    <div>🏢 Supplier: <strong>{msg.extraction.supplier_name}</strong></div>
                    <div>📄 Invoice #: <code className="text-slate-300 font-mono">{msg.extraction.invoice_number}</code></div>
                    <div>💰 Total: <strong>₹{msg.extraction.total_amount?.toLocaleString('en-IN')}</strong></div>
                    <div className="mt-2 pt-2 border-t border-white/10">
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-rose-500/20 text-rose-300 border border-rose-500/30">
                        🚨 {msg.extraction.itc_status}: {msg.extraction.blocked_reason}
                      </span>
                    </div>
                  </div>
                )}

                <div className={`text-[9px] mt-1.5 flex items-center justify-end gap-1 ${msg.sender === 'user' ? 'text-emerald-200' : 'text-slate-400'}`}>
                  <span>{msg.timestamp}</span>
                  {msg.sender === 'user' && <CheckCheck className="w-3 h-3 text-emerald-300" />}
                </div>
              </div>

              {msg.sender === 'user' && (
                <div className="w-7 h-7 rounded-full bg-sky-500/20 text-sky-400 flex items-center justify-center shrink-0 mt-1">
                  <User className="w-4 h-4" />
                </div>
              )}
            </div>
          ))}

          {isProcessing && (
            <div className="flex items-center space-x-2 text-xs text-emerald-400 bg-emerald-500/10 px-3 py-2 rounded-xl w-max">
              <Sparkles className="w-4 h-4 animate-spin" />
              <span>Munim.ai Assistant is typing...</span>
            </div>
          )}
        </div>

        {/* WhatsApp Footer Input Controls */}
        <div className="bg-slate-900/90 p-4 border-t border-white/10 flex items-center space-x-3">
          
          <label className="p-2 rounded-xl text-slate-400 hover:text-emerald-400 hover:bg-emerald-500/10 transition-all cursor-pointer">
            <Paperclip className="w-5 h-5" />
            <input type="file" onChange={handleFileUpload} accept="image/*,.pdf" className="hidden" />
          </label>

          <button
            onClick={() => handleSendMessage('Upload sample bill')}
            className="hidden sm:flex items-center space-x-1 px-3 py-1.5 rounded-lg text-xs font-medium text-slate-300 bg-white/5 hover:bg-white/10 border border-white/5"
          >
            <ImageIcon className="w-3.5 h-3.5 text-emerald-400" />
            <span>Sample Invoice</span>
          </button>

          <input
            type="text"
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSendMessage()}
            placeholder="Type a message or drop an invoice..."
            className="flex-1 bg-slate-950/80 border border-white/10 rounded-xl px-4 py-2.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500/50"
          />

          <button
            onClick={() => handleSendMessage()}
            className="p-2.5 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold transition-all glow-emerald"
          >
            <Send className="w-4 h-4" />
          </button>
        </div>

      </div>

    </div>
  );
}
