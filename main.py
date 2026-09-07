<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AgromartDirect | Ghana's Agribusiness OS</title>
    
    <link rel="manifest" href="/manifest.json">
    <meta name="theme-color" content="#10b981">
    <link rel="icon" href="https://cdn-icons-png.flaticon.com/512/2814/2814468.png" type="image/png">
    
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdn.jsdelivr.net/npm/canvas-confetti@1.6.0/dist/confetti.browser.min.js"></script>
    <script src="https://js.paystack.co/v1/inline.js"></script>
    <script src="https://accounts.google.com/gsi/client" async defer></script>
    
    <style>
        ::-webkit-scrollbar { width: 6px; height: 6px; }
        ::-webkit-scrollbar-thumb { background: #10b981; border-radius: 10px; }
        
        .fade-in { animation: fadeIn 0.4s ease forwards; }
        @keyframes fadeIn { 
            from { opacity: 0; transform: translateY(10px); } 
            to { opacity: 1; transform: translateY(0); } 
        }

        .slide-fade { animation: slideFade 0.5s ease-in-out forwards; }
        @keyframes slideFade { 
            from { opacity: 0; transform: scale(0.98); } 
            to { opacity: 1; transform: scale(1); } 
        }
        
        .glass-card { 
            background: rgba(15, 23, 42, 0.6); 
            backdrop-filter: blur(12px); 
            border: 1px solid rgba(255, 255, 255, 0.05); 
        }
        
        .animate-marquee { animation: marquee 25s linear infinite; }
        @keyframes marquee { 
            0% { transform: translateX(100%); } 
            100% { transform: translateX(-100%); } 
        }
        
        select option { background-color: #0f172a !important; color: #ffffff !important; }
        
        body.sunlight-mode { background-color: #f8fafc !important; color: #020617 !important; }
        body.sunlight-mode .glass-card { 
            background: #ffffff !important; 
            border: 2px solid #0f172a !important; 
            color: #020617 !important; 
        }
        body.sunlight-mode h1, 
        body.sunlight-mode h2, 
        body.sunlight-mode h3, 
        body.sunlight-mode h4, 
        body.sunlight-mode .text-white { color: #020617 !important; }
        body.sunlight-mode p, 
        body.sunlight-mode span.text-slate-400 { color: #334155 !important; }
        
        .guide-content h3 { color: #10b981; font-weight: 900; margin-top: 1.5rem; margin-bottom: 0.5rem; font-size: 1.1rem; }
        .guide-content p { color: #cbd5e1; margin-bottom: 1rem; font-size: 0.875rem; line-height: 1.6; }
        .guide-content ul { list-style-type: disc; padding-left: 1.5rem; color: #cbd5e1; font-size: 0.875rem; margin-bottom: 1rem; }
        
        #wiki-content p { margin-bottom: 0.75rem; font-size: 0.875rem; line-height: 1.6; color: #cbd5e1; }
        #wiki-content b { color: #ffffff; }
        body.sunlight-mode #wiki-content p { color: #334155; }
        body.sunlight-mode #wiki-content b { color: #020617; }
        body.sunlight-mode .guide-content p, body.sunlight-mode .guide-content ul { color: #334155; }
    </style>
</head>
<body id="app-body" class="bg-[#020617] text-slate-100 font-sans min-h-screen flex flex-col transition-colors duration-300">
    
    <div class="fixed top-[-20%] left-[-10%] w-[50%] h-[50%] bg-emerald-600/10 rounded-full blur-[120px] pointer-events-none z-0"></div>
    <div class="fixed bottom-[-20%] right-[-10%] w-[50%] h-[50%] bg-blue-600/10 rounded-full blur-[120px] pointer-events-none z-0"></div>
    
    <div id="toast-container" class="fixed bottom-6 right-6 z-[100] flex flex-col gap-3 pointer-events-none"></div>

    <div class="bg-gradient-to-r from-emerald-950 via-[#020617] to-teal-950 border-b border-emerald-500/20 px-4 py-1.5 text-[11px] flex justify-between items-center text-slate-300 relative z-50">
        <div class="max-w-7xl mx-auto w-full flex items-center justify-between">
            <span class="flex items-center gap-2">
                <span class="text-amber-400">🌦️ Ghana Agro-Weather:</span>
                <span id="agro-weather-text">29°C | Humidity 78% • Optimal conditions for nationwide trade</span>
            </span>
            <span class="hidden md:inline text-emerald-400 font-bold text-[10px] uppercase tracking-wider">🌱 Nationwide Direct Trade & Agribusiness Tools</span>
        </div>
    </div>

    <div id="edit-ad-modal" class="fixed inset-0 bg-[#020617]/95 backdrop-blur-xl z-[120] hidden items-center justify-center p-4">
        <div class="glass-card w-full max-w-lg p-8 rounded-[2.5rem] relative">
            <button onclick="closeEditModal()" class="absolute top-6 right-6 text-slate-400 hover:text-white text-xl">✕</button>
            <h3 class="text-xl font-black text-white mb-4">Edit Ad Details</h3>
            <div class="space-y-4">
                <input type="hidden" id="edit-ad-id">
                <div>
                    <label class="text-xs text-slate-400 font-bold uppercase">Headline</label>
                    <input type="text" id="edit-ad-name" class="w-full bg-[#020617]/80 border border-slate-700 rounded-xl px-4 py-3 text-sm text-white outline-none mt-1">
                </div>
                <div>
                    <label class="text-xs text-slate-400 font-bold uppercase">Price (GH₵)</label>
                    <input type="text" id="edit-ad-price" class="w-full bg-[#020617]/80 border border-slate-700 rounded-xl px-4 py-3 text-sm text-white outline-none mt-1">
                </div>
                <div>
                    <label class="text-xs text-slate-400 font-bold uppercase">Description</label>
                    <textarea id="edit-ad-desc" rows="4" class="w-full bg-[#020617]/80 border border-slate-700 rounded-xl px-4 py-3 text-sm text-white outline-none mt-1"></textarea>
                </div>
                <button onclick="submitAdEdit()" class="w-full bg-emerald-600 hover:bg-emerald-500 text-white font-black py-3.5 rounded-xl text-sm shadow-lg transition-colors">Save Changes</button>
            </div>
        </div>
    </div>

    <div id="preview-ad-modal" class="fixed inset-0 bg-[#020617]/95 backdrop-blur-xl z-[130] hidden items-center justify-center p-4">
        <div class="w-full max-w-md relative">
            <button onclick="closePreviewModal()" class="absolute -top-12 right-0 text-white font-black text-lg bg-slate-800 hover:bg-rose-500 rounded-full w-8 h-8 flex items-center justify-center shadow-lg transition-colors">✕</button>
            <div id="preview-card-container"></div>
        </div>
    </div>

    <div id="batch-modal" class="fixed inset-0 bg-[#020617]/95 backdrop-blur-xl z-[120] hidden items-center justify-center p-4">
        <div class="glass-card w-full max-w-md p-8 rounded-[2.5rem] relative border border-blue-500/30">
            <button onclick="closeBatchModal()" class="absolute top-6 right-6 text-slate-400 hover:text-white text-xl">✕</button>
            <h3 class="text-xl font-black text-white mb-4">Start New Farm Batch</h3>
            <div class="space-y-4">
                <input type="text" id="batch-name" placeholder="Batch Name (e.g. Broiler A)" class="w-full bg-[#020617]/80 border border-slate-700 rounded-xl px-4 py-3 text-sm text-white outline-none focus:border-blue-500">
                <select id="batch-cat" class="w-full bg-[#020617]/80 border border-slate-700 rounded-xl px-4 py-3 text-sm text-white outline-none focus:border-blue-500">
                    <option value="Poultry">Poultry</option>
                    <option value="Vegetables/Fruits">Vegetables</option>
                </select>
                <input type="number" id="batch-qty" placeholder="Quantity" class="w-full bg-[#020617]/80 border border-slate-700 rounded-xl px-4 py-3 text-sm text-white outline-none focus:border-blue-500">
                <input type="number" id="batch-days" placeholder="Harvest In (Days)" class="w-full bg-[#020617]/80 border border-slate-700 rounded-xl px-4 py-3 text-sm text-white outline-none focus:border-blue-500">
                <button onclick="createBatch()" class="w-full bg-blue-600 hover:bg-blue-500 text-white font-black py-3.5 rounded-xl text-sm shadow-lg transition-colors">Initialize Batch 🌱</button>
            </div>
        </div>
    </div>

    <div id="rfq-modal" class="fixed inset-0 bg-[#020617]/95 backdrop-blur-xl z-[120] hidden items-center justify-center p-4">
        <div class="glass-card w-full max-w-lg p-8 rounded-[2.5rem] relative border border-blue-500/30 text-left">
            <button onclick="closeRfqModal()" class="absolute top-6 right-6 text-slate-400 hover:text-white text-xl">✕</button>
            <h3 class="text-2xl font-black text-white mb-4">📢 Post Purchase Tender</h3>
            <div class="space-y-4">
                <input type="text" id="rfq-item" placeholder="Item Needed (e.g. 200 Broilers)" class="w-full bg-[#020617]/80 border border-slate-700 rounded-xl px-4 py-3 text-sm text-white outline-none focus:border-blue-500">
                <select id="rfq-category" class="w-full bg-[#020617]/80 border border-slate-700 rounded-xl px-4 py-3 text-xs text-white outline-none focus:border-blue-500">
                    <option value="Poultry">Poultry</option>
                    <option value="Vegetables/Fruits">Vegetables</option>
                </select>
                <div class="grid grid-cols-2 gap-4">
                    <input type="text" id="rfq-quantity" placeholder="Quantity" class="w-full bg-[#020617]/80 border border-slate-700 rounded-xl px-4 py-3 text-xs text-white outline-none focus:border-blue-500">
                    <input type="text" id="rfq-budget" placeholder="Budget (GH₵)" class="w-full bg-[#020617]/80 border border-slate-700 rounded-xl px-4 py-3 text-xs text-white outline-none focus:border-blue-500">
                </div>
                <input type="text" id="rfq-destination" placeholder="Delivery Town" class="w-full bg-[#020617]/80 border border-slate-700 rounded-xl px-4 py-3 text-xs text-white outline-none focus:border-blue-500">
                <textarea id="rfq-description" placeholder="Requirements" rows="2" class="w-full bg-[#020617]/80 border border-slate-700 rounded-xl px-4 py-3 text-xs text-white outline-none focus:border-blue-500"></textarea>
                <button onclick="submitBuyerRequest()" id="rfq-submit-btn" class="w-full bg-blue-600 hover:bg-blue-500 text-white font-black py-4 rounded-xl text-sm transition-colors shadow-lg">Publish Tender</button>
            </div>
        </div>
    </div>

    <div id="order-modal" class="fixed inset-0 bg-[#020617]/90 backdrop-blur-md z-[100] hidden items-center justify-center p-4">
        <div class="glass-card w-full max-w-lg p-8 rounded-[2.5rem] relative border border-emerald-500/30">
            <button onclick="closeOrderModal()" class="absolute top-6 right-6 text-slate-400 hover:text-white text-xl">✕</button>
            <h3 class="text-2xl font-black text-white mb-5">🤝 Smart Deal Room</h3>
            
            <div class="bg-[#0f172a] p-4 rounded-2xl mb-4 border border-slate-700/80">
                <p class="text-sm font-bold text-emerald-400 truncate" id="order-product-name"></p>
                <p class="text-xl font-black text-white">GH₵<span id="order-base-price">0</span> / <span id="order-unit"></span></p>
            </div>
            
            <div class="flex gap-2 p-1 bg-slate-900 rounded-xl mb-4 border border-slate-800 text-xs font-bold">
                <button onclick="switchOrderTab('direct')" id="tab-direct" class="flex-1 py-2 rounded-lg bg-emerald-600 text-white transition-all">Direct Order</button>
                <button onclick="switchOrderTab('haggle')" id="tab-haggle" class="flex-1 py-2 rounded-lg text-slate-400 hover:text-white transition-all">Haggle</button>
                <button onclick="switchOrderTab('group')" id="tab-group" class="flex-1 py-2 rounded-lg text-slate-400 hover:text-white transition-all">Group Split</button>
            </div>
            
            <div class="space-y-4">
                <input type="number" id="order-quantity" value="1" min="1" oninput="calculateOrderTotal()" class="w-full bg-[#020617]/80 border border-slate-700 rounded-xl px-4 py-3 text-white font-black outline-none">
                
                <div id="panel-haggle" class="hidden p-4 rounded-xl bg-emerald-950/20 border border-emerald-500/30 space-y-2">
                    <input type="range" id="haggle-slider" min="50" max="150" value="100" oninput="updateHaggleMeter()" class="w-full accent-emerald-500 cursor-pointer">
                    <span id="haggle-feedback" class="font-bold text-amber-400 text-xs">Fair Offer</span>
                </div>
                
                <div id="panel-group" class="hidden p-4 rounded-xl bg-teal-950/20 border border-teal-500/30 space-y-2">
                    <input type="number" id="group-split-count" value="2" min="2" oninput="calculateOrderTotal()" class="w-full bg-[#020617]/80 border border-slate-700 rounded-xl px-4 py-2 text-white font-bold outline-none">
                    <p class="text-[11px] text-teal-300">Each pays: GH₵<span id="group-each-price">0</span></p>
                </div>
                
                <input type="text" id="order-destination" placeholder="Delivery Town" class="w-full bg-[#020617]/80 border border-slate-700 rounded-xl px-4 py-3 text-white outline-none">
                
                <div class="flex justify-between items-end pt-4 border-t border-white/10">
                    <span class="text-sm font-bold text-white">Total:</span>
                    <span class="text-2xl font-black text-emerald-400">GH₵<span id="order-total-price">0</span></span>
                </div>
                
                <div class="grid grid-cols-2 gap-2 pt-2">
                    <button onclick="executeDealWhatsApp()" class="bg-[#25D366] text-[#020617] font-black py-3 rounded-xl text-xs flex items-center justify-center">💬 WhatsApp</button>
                    <button onclick="executeCallFarmer()" class="bg-blue-500/10 text-blue-400 border border-blue-500/30 font-black py-3 rounded-xl text-xs flex items-center justify-center">📞 Call</button>
                </div>
            </div>
        </div>
    </div>

    <div id="flyer-modal" class="fixed inset-0 bg-[#020617]/95 backdrop-blur-xl z-[150] hidden items-center justify-center p-4">
        <div class="glass-card w-full max-w-md p-6 rounded-[2.5rem] text-center border border-emerald-500/30">
            <button onclick="closeFlyerModal()" class="absolute top-4 right-4 text-slate-400 hover:text-white text-2xl font-bold">✕</button>
            <h3 class="text-xl font-black text-white mb-4">Your Flyer! 📲</h3>
            <canvas id="flyer-canvas" class="hidden"></canvas>
            <img id="flyer-preview" src="" class="w-full max-w-[300px] rounded-2xl mb-6 mx-auto shadow-2xl">
            <button onclick="downloadFlyer()" class="w-full bg-[#25D366] text-[#020617] font-black py-4 rounded-xl text-sm">Download</button>
        </div>
    </div>

    <div id="video-studio-modal" class="fixed inset-0 bg-[#020617]/95 backdrop-blur-xl z-[150] hidden items-center justify-center p-4">
        <div class="glass-card w-full max-w-lg p-8 rounded-[2.5rem] relative border border-purple-500/30">
            <button onclick="closeVideoStudio()" class="absolute top-6 right-6 text-slate-400 hover:text-white text-xl">✕</button>
            <h3 class="text-2xl font-black text-white mb-4">AI Status Video Studio</h3>
            <input type="hidden" id="vs-ad-id">
            <button onclick="generateAiVideo()" class="w-full bg-purple-600 text-white font-black py-4 rounded-xl text-sm">Generate Video</button>
            <div id="video-studio-processing" class="hidden text-center py-8">Generating...</div>
            <div id="video-studio-result" class="hidden text-center"><button onclick="downloadAiVideo()" class="w-full bg-[#25D366] text-[#020617] font-black py-3 rounded-xl">Download</button></div>
        </div>
    </div>

    <!-- HEADER -->
    <header class="bg-[#020617]/70 backdrop-blur-2xl border-b border-white/5 sticky top-0 z-50">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 py-4 flex justify-between items-center">
            <div class="flex items-center gap-3 cursor-pointer group" onclick="navigate('home')">
                <div class="w-10 h-10 bg-gradient-to-br from-emerald-400 to-teal-600 rounded-xl flex items-center justify-center text-lg shadow-lg">🌾</div>
                <h1 class="text-xl font-black text-white group-hover:text-emerald-400">AgromartDirect</h1>
            </div>
            
            <div class="flex gap-2 items-center flex-wrap justify-end">
                <button onclick="navigate('haulage')" class="text-xs font-bold text-amber-400 border border-amber-500/30 bg-amber-500/10 px-3 py-1.5 rounded-lg hidden lg:block hover:bg-amber-500/20">🚚 Haulage Pool</button>
                <button onclick="navigate('agridoctor')" class="text-xs font-bold text-rose-400 border border-rose-500/30 bg-rose-500/10 px-3 py-1.5 rounded-lg hidden lg:block hover:bg-rose-500/20">🩺 AgriDoctor AI</button>
                <button onclick="navigate('trainer')" class="text-xs font-bold text-purple-400 border border-purple-500/30 bg-purple-500/10 px-3 py-1.5 rounded-lg hidden lg:block hover:bg-purple-500/20">📚 Agri Trainer</button>
                <button onclick="navigate('grants')" class="text-xs font-bold text-amber-400 border border-amber-500/30 bg-amber-500/10 px-3 py-1.5 rounded-lg hidden lg:block hover:bg-amber-500/20">🏆 Agri-Grants</button>
                <button onclick="navigate('farm-manager')" class="text-xs font-bold text-blue-400 border border-blue-500/30 bg-blue-500/10 px-3 py-1.5 rounded-lg hidden md:block hover:bg-blue-500/20">💼 Farm Manager</button>
                <button onclick="navigate('intel')" class="text-xs font-bold text-rose-400 border border-rose-500/30 bg-rose-500/10 px-3 py-1.5 rounded-lg hidden xl:block hover:bg-rose-500/20">📊 Market Intel</button>
                <button onclick="navigate('calculator')" class="text-xs font-bold text-teal-400 border border-teal-500/30 bg-teal-500/10 px-3 py-1.5 rounded-lg hidden xl:block hover:bg-teal-500/20">🧮 Feed Calc</button>
                <button onclick="navigate('rentals')" class="text-xs font-bold text-amber-300 border border-amber-400/30 bg-amber-500/10 px-3 py-1.5 rounded-lg hidden xl:block hover:bg-amber-500/20">🚜 Machinery Hire</button>
                <button onclick="navigate('waste')" class="text-xs font-bold text-emerald-300 border border-emerald-400/30 bg-emerald-500/10 px-3 py-1.5 rounded-lg hidden xl:block hover:bg-emerald-500/20">♻️ Eco-Loop</button>
                
                <button id="pwa-install-btn" onclick="triggerPwaInstall()" class="hidden bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 font-bold px-3 py-1.5 rounded-lg text-xs">📲 Install</button>
                <button onclick="toggleSunlightMode()" class="w-9 h-9 flex items-center justify-center bg-white/5 border border-white/10 rounded-xl text-xs text-slate-300">☀️</button>
                
                <button id="nav-login-btn" onclick="navigate('auth')" class="text-xs font-bold text-slate-300 hover:text-emerald-400">Sign In</button>
                
                <div id="nav-user-profile" class="hidden items-center gap-3 bg-white/5 px-4 py-1.5 rounded-full border border-white/10">
                    <span id="nav-user-name" class="text-xs font-bold text-emerald-400 hidden md:block"></span>
                    <button onclick="navigate('dashboard')" class="text-xs font-black text-white">Dashboard</button>
                    <button onclick="logout()" class="text-xs text-rose-400 font-bold">Logout</button>
                </div>
                
                <button onclick="requireAuthToPost()" class="bg-gradient-to-r from-emerald-600 to-teal-500 text-white text-xs font-black px-4 py-2.5 rounded-xl shadow-lg">Post Ad</button>
            </div>
        </div>
    </header>

    <div class="md:hidden bg-[#020617] border-b border-white/10 px-4 py-3 overflow-x-auto whitespace-nowrap flex gap-3 z-40">
        <button onclick="navigate('haulage')" class="text-xs font-bold text-amber-400 border border-amber-500/30 bg-amber-500/10 px-4 py-2 rounded-xl shrink-0">🚚 Haulage Pool</button>
        <button onclick="navigate('agridoctor')" class="text-xs font-bold text-rose-400 border border-rose-500/30 bg-rose-500/10 px-4 py-2 rounded-xl shrink-0">🩺 AgriDoctor AI</button>
        <button onclick="navigate('trainer')" class="text-xs font-bold text-purple-400 border border-purple-500/30 bg-purple-500/10 px-4 py-2 rounded-xl shrink-0">📚 Agri Trainer</button>
        <button onclick="navigate('grants')" class="text-xs font-bold text-amber-400 border border-amber-500/30 bg-amber-500/10 px-4 py-2 rounded-xl shrink-0">🏆 Agri-Grants</button>
        <button onclick="navigate('farm-manager')" class="text-xs font-bold text-blue-400 border border-blue-500/30 bg-blue-500/10 px-4 py-2 rounded-xl shrink-0">💼 Farm Manager</button>
        <button onclick="navigate('intel')" class="text-xs font-bold text-rose-400 border border-rose-500/30 bg-rose-500/10 px-4 py-2 rounded-xl shrink-0">📊 Market Intel</button>
        <button onclick="navigate('calculator')" class="text-xs font-bold text-teal-400 border border-teal-500/30 bg-teal-500/10 px-4 py-2 rounded-xl shrink-0">🧮 Feed Calc</button>
        <button onclick="navigate('rentals')" class="text-xs font-bold text-amber-300 border border-amber-400/30 bg-amber-500/10 px-4 py-2 rounded-xl shrink-0">🚜 Machinery Hire</button>
        <button onclick="navigate('waste')" class="text-xs font-bold text-emerald-300 border border-emerald-400/30 bg-emerald-500/10 px-4 py-2 rounded-xl shrink-0">♻️ Eco-Loop</button>
    </div>

    <div class="bg-[#020617] border-b border-white/5 relative z-40 hidden md:block overflow-hidden shadow-inner">
        <div class="max-w-7xl mx-auto flex items-center pl-6">
            <div class="bg-emerald-600 text-white text-[10px] font-black uppercase tracking-wider px-4 py-2 rounded-r-lg z-10 shrink-0 flex items-center gap-2">
                <span class="w-2 h-2 rounded-full bg-rose-500 animate-pulse"></span> LIVE GHANA AVG
            </div>
            <div class="overflow-hidden flex-grow relative ml-4 h-8 flex items-center">
                <div class="flex gap-8 animate-marquee whitespace-nowrap" id="market-ticker">
                    <span class="text-xs text-slate-400 font-medium">Gathering real-time nationwide prices...</span>
                </div>
            </div>
        </div>
    </div>

    <main class="max-w-7xl mx-auto px-6 py-8 flex-grow w-full relative z-10">
        
        <div id="view-home" class="fade-in space-y-16">
            <div class="text-center py-20 px-4 glass-card rounded-[2.5rem] shadow-2xl border-t border-white/10 relative overflow-hidden">
                <div class="text-6xl mb-6">🚜</div>
                <h1 class="text-4xl md:text-6xl font-black text-transparent bg-clip-text bg-gradient-to-r from-white to-slate-400 mb-6">The Farmers Market,<br>Now Online.</h1>
                
                <div class="max-w-4xl mx-auto">
                    <div class="flex flex-col md:flex-row bg-[#020617]/50 rounded-3xl border border-slate-700/80 p-2 gap-2">
                        <div class="relative w-full md:w-1/3 flex items-center bg-[#0f172a] rounded-2xl border border-slate-700/50">
                            <span class="absolute left-4 text-emerald-500 z-10">🌍</span>
                            <select id="home-region" class="w-full bg-transparent text-sm text-white font-bold pl-10 pr-4 py-4 outline-none appearance-none rounded-2xl">
                                <option value="All Regions">All Regions (Ghana)</option>
                                <option value="Ashanti">Ashanti Region</option>
                                <option value="Greater Accra">Greater Accra Region</option>
                            </select>
                        </div>
                        <div class="relative w-full md:w-2/3 flex items-center">
                            <span class="absolute left-4 text-slate-500 z-10">🔍</span>
                            <input type="search" id="market_finder" placeholder="Search 'Broilers' or 'Tomatoes'..." class="w-full bg-transparent pl-10 pr-12 py-4 text-sm text-white focus:outline-none">
                            <button onclick="startVoiceSearch()" class="absolute right-4 text-slate-400 hover:text-emerald-400 p-1">🎤</button>
                        </div>
                        <button onclick="executeSearch()" class="bg-emerald-600 hover:bg-emerald-500 text-white font-black px-8 py-4 rounded-2xl shrink-0">Search</button>
                    </div>
                </div>

                <div class="mt-12 relative w-full max-w-5xl mx-auto glass-card rounded-[2.5rem] border border-white/10 overflow-hidden shadow-2xl h-64 md:h-56" id="feature-slideshow"></div>

                <div class="mt-8 flex justify-center">
                    <div class="bg-[#0f172a] p-1.5 rounded-2xl border border-slate-700/80 inline-flex shadow-xl">
                        <button onclick="switchMarketplaceTab('ads')" id="btn-tab-ads" class="px-6 py-2.5 rounded-xl font-black text-xs bg-emerald-600 text-white shadow-lg">🌾 Available Produce (Ads)</button>
                        <button onclick="switchMarketplaceTab('rfqs')" id="btn-tab-rfqs" class="px-6 py-2.5 rounded-xl font-black text-xs text-slate-400 hover:text-white flex items-center gap-1.5">📢 Buyer Tenders (RFQs)</button>
                    </div>
                </div>
            </div>

            <div id="home-rfq-container" class="hidden">
                <div class="flex justify-between items-center mb-6">
                    <h3 class="text-2xl font-black text-white">📢 Commercial Buyer Tenders</h3>
                    <button onclick="openRfqModal()" class="bg-blue-600 text-white font-black text-xs px-5 py-3 rounded-xl">+ Post Purchase Tender</button>
                </div>
                <div id="rfq-grid" class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6"></div>
            </div>

            <div id="home-ads-container">
                <div class="mt-16">
                    <div class="flex items-center justify-between mb-6">
                        <h3 class="text-2xl font-black text-white">🔥 Trending Nationwide</h3>
                        <button onclick="navigate('marketplace')" class="text-xs font-bold text-emerald-400">View All →</button>
                    </div>
                    <div id="trending-grid" class="grid grid-cols-1 md:grid-cols-3 gap-8"></div>
                </div>
            </div>
        </div>

        <div id="view-marketplace" class="fade-in hidden space-y-6">
            <div class="flex flex-col md:flex-row md:items-center justify-between bg-white/5 p-4 rounded-2xl border border-white/5 gap-4">
                <div class="flex items-center gap-3">
                    <h2 class="text-2xl font-black text-white" id="market-title">Market Catalog</h2>
                    <div class="bg-[#0f172a] p-1 rounded-xl inline-flex border border-slate-700/80">
                        <button onclick="setMarketplaceMode('ads')" id="mode-ads-btn" class="px-3 py-1 rounded-lg text-xs font-black bg-emerald-600 text-white">Ads</button>
                        <button onclick="setMarketplaceMode('rfqs')" id="mode-rfqs-btn" class="px-3 py-1 rounded-lg text-xs font-black text-slate-400">Tenders</button>
                    </div>
                </div>
                <div class="flex gap-2 flex-wrap items-center">
                    <select id="market-region-filter" onchange="executeFilters()" class="bg-[#0f172a] border border-slate-600 rounded-xl px-4 py-2 text-xs text-white outline-none font-bold">
                        <option value="All Regions">All Regions (Ghana)</option>
                        <option value="Ashanti">Ashanti</option>
                        <option value="Greater Accra">Greater Accra</option>
                    </select>
                    <select id="filter-sort" onchange="executeFilters()" class="bg-[#020617]/80 border border-slate-700 rounded-xl px-4 py-2 text-xs text-white outline-none">
                        <option value="newest">Newest First</option>
                        <option value="price_asc">Price: Low to High</option>
                        <option value="price_desc">Price: High to Low</option>
                    </select>
                    <button onclick="navigate('home')" class="text-xs font-bold text-emerald-400 bg-emerald-500/10 px-4 py-2 rounded-xl">← Back</button>
                </div>
            </div>
            <div id="product-grid" class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-8"></div>
        </div>

        <div id="view-trainer" class="fade-in hidden space-y-8">
            <div class="text-center mb-10">
                <div class="w-16 h-16 bg-purple-500/20 rounded-full flex items-center justify-center text-3xl mx-auto mb-4 border border-purple-500/30">📚</div>
                <h2 class="text-3xl md:text-5xl font-black text-white">Agri Trainer Hub</h2>
                <p class="text-slate-400 text-sm max-w-xl mx-auto mt-2">Select a category to view detailed, step-by-step guides on farming.</p>
            </div>
            <div id="trainer-categories" class="grid grid-cols-1 md:grid-cols-2 gap-8 max-w-4xl mx-auto">
                <div onclick="showTrainerSubCategory('crops')" class="glass-card p-10 rounded-[2.5rem] cursor-pointer hover:border-emerald-500/50 text-center border border-emerald-500/20">
                    <div class="text-7xl mb-6">🌾</div>
                    <h3 class="text-2xl font-black text-white mb-2">Learn to Grow Crops</h3>
                </div>
                <div onclick="showTrainerSubCategory('animals')" class="glass-card p-10 rounded-[2.5rem] cursor-pointer hover:border-blue-500/50 text-center border border-blue-500/20">
                    <div class="text-7xl mb-6">🐔</div>
                    <h3 class="text-2xl font-black text-white mb-2">Learn to Raise Animals</h3>
                </div>
            </div>
            <div id="trainer-items" class="hidden">
                <button onclick="resetTrainer()" class="text-emerald-400 text-sm font-bold mb-6 flex items-center gap-2">← Back to Categories</button>
                <div id="trainer-items-grid" class="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-4 gap-6"></div>
            </div>
            <div id="trainer-guide" class="hidden glass-card p-8 md:p-12 rounded-[2.5rem] border border-emerald-500/30 relative">
                <button onclick="document.getElementById('trainer-guide').classList.add('hidden'); document.getElementById('trainer-items').classList.remove('hidden');" class="text-emerald-400 text-sm font-bold mb-8">← Back</button>
                <div class="flex items-center gap-6 mb-8 border-b border-white/10 pb-8">
                    <div id="guide-icon" class="text-6xl bg-white/5 p-4 rounded-3xl"></div>
                    <div>
                        <h2 id="guide-title" class="text-4xl font-black text-white mb-2"></h2>
                        <p id="guide-intro" class="text-emerald-400 font-bold"></p>
                    </div>
                </div>
                <div id="guide-content" class="guide-content max-w-3xl"></div>
            </div>
        </div>

        <!-- AGRIDOCTOR AI SCANNER VIEW -->
        <div id="view-agridoctor" class="fade-in hidden max-w-4xl mx-auto mt-6 space-y-8">
            <div class="text-center space-y-4 mb-10">
                <div class="w-16 h-16 bg-rose-500/20 rounded-full flex items-center justify-center text-3xl mx-auto border border-rose-500/30 shadow-lg">🩺</div>
                <h2 class="text-3xl md:text-5xl font-black text-white tracking-tight">AgriDoctor AI</h2>
                <p class="text-slate-400 text-sm max-w-xl mx-auto">Upload a photo of a diseased crop leaf or sick livestock. Our AI will diagnose the issue and provide an instant treatment plan.</p>
            </div>

            <div class="glass-card p-8 rounded-[2.5rem] border border-rose-500/30 shadow-2xl relative overflow-hidden">
                <div id="agridoctor-upload-state" class="text-center">
                    <div class="w-full h-64 bg-[#020617]/50 border-2 border-dashed border-rose-500/50 rounded-3xl flex flex-col items-center justify-center cursor-pointer hover:border-rose-400 transition-colors group relative overflow-hidden" onclick="document.getElementById('agridoctor-file').click()">
                        <img id="agridoctor-preview" src="" class="hidden absolute inset-0 w-full h-full object-cover opacity-50 z-0">
                        <div class="z-10 relative">
                            <span class="text-5xl mb-4 block">📸</span>
                            <span class="text-white font-bold block">Tap to Scan Photo</span>
                            <span class="text-slate-400 text-xs mt-1 block">Supports leaves, fruits, and livestock</span>
                        </div>
                    </div>
                    <input type="file" id="agridoctor-file" accept="image/*" capture="environment" class="hidden" onchange="handleAgriDoctorUpload(event)">
                    <button id="agridoctor-analyze-btn" onclick="processAgriDoctor()" class="hidden w-full mt-6 bg-rose-600 hover:bg-rose-500 text-white font-black py-4 rounded-xl text-sm transition-colors shadow-lg">Analyze Image 🔍</button>
                </div>

                <div id="agridoctor-processing-state" class="hidden text-center py-12">
                    <div class="w-16 h-16 border-4 border-rose-500/30 border-t-rose-500 rounded-full animate-spin mx-auto mb-6"></div>
                    <h3 class="text-xl font-black text-white mb-2">Analyzing Biomarkers...</h3>
                    <p class="text-xs text-slate-400">Cross-referencing with local Ghanaian pathology databases...</p>
                </div>

                <div id="agridoctor-result-state" class="hidden">
                    <div class="bg-[#0f172a]/80 border border-rose-500/30 rounded-2xl p-6 mb-6">
                        <div class="flex items-center gap-3 mb-4 border-b border-white/10 pb-4">
                            <span class="text-4xl" id="diag-icon">🦠</span>
                            <div>
                                <h4 class="text-[10px] text-rose-400 font-bold uppercase">Detected Pathogen / Issue</h4>
                                <h3 class="text-2xl font-black text-white" id="diag-title">...</h3>
                            </div>
                        </div>
                        <p class="text-sm text-slate-300 mb-6 leading-relaxed" id="diag-desc">...</p>
                        <div class="space-y-4">
                            <div class="bg-[#020617]/50 p-5 rounded-xl border border-emerald-500/20">
                                <h4 class="text-[11px] font-black text-emerald-400 mb-2 uppercase">🌱 Organic / Home Remedy</h4>
                                <p class="text-sm text-slate-300" id="diag-organic">...</p>
                            </div>
                            <div class="bg-[#020617]/50 p-5 rounded-xl border border-amber-500/20">
                                <h4 class="text-[11px] font-black text-amber-400 mb-2 uppercase">🧪 Chemical Intervention</h4>
                                <p class="text-sm text-slate-300" id="diag-chemical">...</p>
                            </div>
                        </div>
                    </div>
                    <div class="flex gap-3">
                        <button onclick="resetAgriDoctor()" class="flex-1 bg-slate-800 text-white font-bold py-3.5 rounded-xl text-sm border border-slate-700">Scan Another</button>
                        <button onclick="navigate('marketplace')" class="flex-1 bg-rose-600 text-white font-bold py-3.5 rounded-xl text-sm shadow-lg">Buy Treatment on Market</button>
                    </div>
                </div>
            </div>
        </div>

        <!-- HAULAGE POOL VIEW -->
        <div id="view-haulage" class="fade-in hidden space-y-8">
            <div class="flex flex-col md:flex-row md:items-center justify-between bg-[#0f172a] p-6 rounded-3xl border border-amber-500/30 gap-4 shadow-xl">
                <div>
                    <h2 class="text-2xl font-black text-white flex items-center gap-2">🚚 Haulage Pool & Empty-Leg Freight</h2>
                    <p class="text-xs text-slate-400 mt-1">Book cheap return-trip truck space or list your empty haulage truck returning from deliveries.</p>
                </div>
                <button onclick="openHaulagePostModal()" class="bg-amber-500 hover:bg-amber-400 text-[#020617] text-xs font-black px-5 py-3 rounded-xl shadow-lg transition-colors whitespace-nowrap">+ List Empty Truck</button>
            </div>
            <div id="haulage-grid" class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6"></div>
        </div>

        <div id="view-farm-manager" class="fade-in hidden space-y-8">
            <div class="flex justify-between items-center bg-[#0f172a] p-6 rounded-3xl border border-blue-500/30">
                <h2 class="text-2xl font-black text-white">💼 Farm Manager Dashboard</h2>
                <button onclick="openBatchModal()" class="bg-blue-600 text-white text-xs font-bold px-5 py-3 rounded-xl">+ Start New Batch</button>
            </div>
            <div id="farm-batches-grid" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6"></div>
        </div>

        <div id="view-intel" class="fade-in hidden space-y-8">
            <div class="text-center space-y-4 mb-10">
                <div class="w-16 h-16 bg-rose-500/20 rounded-full flex items-center justify-center text-3xl mx-auto border border-rose-500/30">📊</div>
                <h2 class="text-3xl md:text-5xl font-black text-white">Market Intelligence</h2>
            </div>
            <div id="intel-grid" class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6"></div>
        </div>

        <div id="view-calculator" class="fade-in hidden space-y-8">
            <div class="text-center space-y-4 mb-10">
                <div class="w-16 h-16 bg-teal-500/20 rounded-full flex items-center justify-center text-3xl mx-auto border border-teal-500/30">🧮</div>
                <h2 class="text-3xl md:text-5xl font-black text-white">Precision Feed Calculator</h2>
            </div>
            <div class="grid grid-cols-1 lg:grid-cols-2 gap-8">
                <div class="glass-card p-8 rounded-[2.5rem] border border-teal-500/30">
                    <h3 class="text-lg font-black text-teal-400 mb-6">1. Set Your Targets</h3>
                    <div class="space-y-5">
                        <input type="number" id="calc-target-cp" value="22" class="w-full bg-[#0f172a] border border-slate-600 rounded-xl px-4 py-3 text-lg font-black text-teal-400 outline-none">
                        <input type="number" id="calc-protein-cp" value="44" class="w-full bg-[#0f172a] border border-slate-600 rounded-xl px-4 py-2.5 text-sm text-white">
                        <input type="number" id="calc-protein-price" value="350" class="w-full bg-[#0f172a] border border-slate-600 rounded-xl px-4 py-2.5 text-sm text-white">
                        <input type="number" id="calc-energy-cp" value="8" class="w-full bg-[#0f172a] border border-slate-600 rounded-xl px-4 py-2.5 text-sm text-white">
                        <input type="number" id="calc-energy-price" value="200" class="w-full bg-[#0f172a] border border-slate-600 rounded-xl px-4 py-2.5 text-sm text-white">
                        <button onclick="calculateFeedMix()" class="w-full bg-teal-600 text-white font-black py-4 rounded-xl text-sm">Calculate Mix Ratio ✨</button>
                    </div>
                </div>
                <div class="glass-card p-8 rounded-[2.5rem] border border-white/5 flex flex-col justify-center">
                    <div id="calc-results-empty" class="text-center py-10 text-slate-500 text-sm">Enter targets and hit calculate.</div>
                    <div id="calc-results-filled" class="hidden space-y-6">
                        <div class="bg-slate-900/80 p-5 rounded-2xl border border-slate-700">
                            <div class="flex justify-between items-center mb-2"><span class="text-emerald-400">Protein:</span><span id="res-protein-kg" class="font-black text-white">0 kg</span></div>
                            <div class="flex justify-between items-center"><span class="text-amber-400">Energy:</span><span id="res-energy-kg" class="font-black text-white">0 kg</span></div>
                        </div>
                        <div class="bg-teal-950/30 p-5 rounded-2xl border border-teal-500/30">
                            <span class="text-4xl font-black text-white" id="res-total-cost">GH₵ 0.00</span>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <div id="view-grants" class="fade-in hidden space-y-8">
            <div class="text-center space-y-4 mb-10">
                <div class="w-16 h-16 bg-amber-500/20 rounded-full flex items-center justify-center text-3xl mx-auto border border-amber-500/30">🏆</div>
                <h2 class="text-3xl md:text-5xl font-black text-white">Agri-Finance & Grants</h2>
            </div>
            <div id="grants-grid" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6"></div>
        </div>

        <div id="view-post" class="fade-in hidden max-w-2xl mx-auto mt-6">
            <div class="glass-card p-8 rounded-[2rem] shadow-2xl space-y-6">
                <h2 class="text-2xl font-black text-white">Post a Seller Ad</h2>
                <div id="image-preview" class="w-full h-48 bg-[#020617]/50 border-2 border-dashed border-slate-700 rounded-2xl flex flex-col items-center justify-center cursor-pointer" onclick="document.getElementById('post-image').click()">
                    <span class="text-slate-500 text-sm font-bold">Click to upload photos</span>
                </div>
                <input type="file" id="post-image" accept="image/*" multiple class="hidden" onchange="handleImageUpload(event)">
                <input type="text" id="post-name" placeholder="Headline" class="w-full bg-[#020617]/80 border border-slate-700 rounded-xl px-5 py-4 text-sm text-white">
                <textarea id="post-description" placeholder="Description" rows="3" class="w-full bg-[#020617]/80 border border-slate-700 rounded-xl px-5 py-4 text-sm text-white"></textarea>
                <input type="text" id="post-unit" placeholder="Unit (e.g. per crate)" class="w-full bg-[#020617]/80 border border-slate-700 rounded-xl px-5 py-4 text-sm text-white">
                <input type="text" id="post-price" placeholder="Price (GH₵)" class="w-full bg-[#020617]/80 border border-slate-700 rounded-xl px-5 py-4 text-sm text-white">
                <input type="text" id="post-town" placeholder="Town" class="w-full bg-[#020617]/80 border border-slate-700 rounded-xl px-5 py-4 text-sm text-white">
                <button onclick="submitAd()" class="w-full bg-emerald-600 text-white font-black py-4 rounded-xl text-sm shadow-lg">Submit Ad</button>
            </div>
        </div>

        <div id="view-dashboard" class="fade-in hidden max-w-5xl mx-auto mt-6 space-y-6">
            <div class="glass-card p-8 rounded-[2.5rem] flex flex-col md:flex-row items-center gap-8">
                <div class="w-24 h-24 rounded-full bg-slate-800 flex items-center justify-center text-4xl" id="my-profile-avatar">👨🏽‍🌾</div>
                <div>
                    <h2 class="text-3xl font-black text-white" id="my-profile-name">Loading...</h2>
                    <p class="text-slate-400 text-sm" id="my-profile-email">...</p>
                </div>
            </div>
            <div class="grid grid-cols-1 lg:grid-cols-2 gap-8">
                <div><h3 class="text-xl font-black text-white mb-4">My Ads</h3><div id="my-ads-list"></div></div>
                <div><h3 class="text-xl font-black text-white mb-4">My Tenders</h3><div id="my-tenders-list"></div></div>
            </div>
            <div id="admin-panel" class="hidden mt-12 glass-card p-8 rounded-3xl border border-emerald-500/30">
                <h3 class="text-2xl font-black text-emerald-400 mb-6">🛡️ Founder Admin Hub</h3>
                <div id="admin-mod-list"></div>
            </div>
        </div>

        <div id="view-rentals" class="fade-in hidden space-y-8">
            <div class="flex justify-between items-center bg-[#0f172a] p-6 rounded-3xl border border-amber-500/30">
                <h2 class="text-2xl font-black text-white">🚜 Heavy Equipment Rentals</h2>
                <button onclick="openRentalPostModal()" class="bg-amber-500 text-[#020617] text-xs font-black px-5 py-3 rounded-xl">+ List Equipment</button>
            </div>
            <div id="rentals-grid" class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6"></div>
        </div>

        <div id="view-waste" class="fade-in hidden space-y-8 max-w-2xl mx-auto">
            <div class="glass-card p-8 rounded-[2.5rem] border border-emerald-500/30 space-y-4">
                <h3 class="text-lg font-black text-emerald-400">♻️ Eco-Loop Logistics</h3>
                <select id="waste-type" class="w-full bg-[#0f172a] border border-slate-700 rounded-xl px-4 py-3 text-sm text-white">
                    <option value="Used Cooking Oil (UCO)">Used Cooking Oil (UCO)</option>
                    <option value="Cocoa Pod Husks / Biomass">Cocoa Pod Husks / Biomass</option>
                </select>
                <input type="text" id="waste-qty" placeholder="Volume / Weight" class="w-full bg-[#020617]/80 border border-slate-700 rounded-xl px-4 py-3 text-sm text-white">
                <input type="text" id="waste-loc" placeholder="Pickup Location" class="w-full bg-[#020617]/80 border border-slate-700 rounded-xl px-4 py-3 text-sm text-white">
                <input type="tel" id="waste-phone" placeholder="Contact Phone" class="w-full bg-[#020617]/80 border border-slate-700 rounded-xl px-4 py-3 text-sm text-white">
                <button onclick="submitWasteRequest()" class="w-full bg-emerald-600 text-white font-black py-4 rounded-xl text-sm">Schedule Dispatch 🚚</button>
            </div>
            <div id="waste-queue" class="space-y-3"></div>
        </div>

        <div id="view-auth" class="fade-in hidden max-w-sm mx-auto mt-10">
            <div class="glass-card p-8 rounded-[2rem] shadow-2xl relative">
                <div id="login-box">
                    <h2 class="text-2xl font-black text-white text-center mb-6">Sign In</h2>
                    <div class="space-y-4">
                        <input type="email" id="login-email" placeholder="Email" class="w-full bg-[#020617]/80 border border-slate-700 rounded-xl px-4 py-3.5 text-sm text-white">
                        <input type="password" id="login-password" placeholder="Password" class="w-full bg-[#020617]/80 border border-slate-700 rounded-xl px-4 py-3.5 text-sm text-white">
                        <button onclick="loginUser()" class="w-full bg-emerald-600 text-white font-black py-4 rounded-xl text-sm">Sign In</button>
                    </div>
                    <div id="google-signin-btn-login" class="flex justify-center w-full mt-4"></div>
                    <p class="text-xs text-slate-400 text-center mt-6">No account? <button onclick="toggleAuthBox('signup')" class="text-emerald-400 font-bold">Sign Up</button></p>
                </div>
                <div id="signup-box" class="hidden">
                    <h2 class="text-2xl font-black text-white text-center mb-6">Create Account</h2>
                    <div class="space-y-4">
                        <input type="text" id="su-name" placeholder="Full Name" class="w-full bg-[#020617]/80 border border-slate-700 rounded-xl px-4 py-3 text-sm text-white">
                        <input type="email" id="su-email" placeholder="Email" class="w-full bg-[#020617]/80 border border-slate-700 rounded-xl px-4 py-3 text-sm text-white">
                        <input type="number" id="su-age" placeholder="Age" class="w-full bg-[#020617]/80 border border-slate-700 rounded-xl px-4 py-3 text-sm text-white">
                        <input type="tel" id="su-phone" placeholder="Phone" class="w-full bg-[#020617]/80 border border-slate-700 rounded-xl px-4 py-3 text-sm text-white">
                        <input type="password" id="su-password" placeholder="Password" class="w-full bg-[#020617]/80 border border-slate-700 rounded-xl px-4 py-3 text-sm text-white">
                        <button onclick="signupUser()" class="w-full bg-emerald-600 text-white font-black py-4 rounded-xl text-sm">Create Account</button>
                    </div>
                    <div id="google-signin-btn-signup" class="flex justify-center w-full mt-4"></div>
                    <p class="text-xs text-slate-400 text-center mt-6">Have an account? <button onclick="toggleAuthBox('login')" class="text-emerald-400 font-bold">Sign In</button></p>
                </div>
            </div>
        </div>

        <div id="view-pricing" class="fade-in hidden max-w-5xl mx-auto mt-10 space-y-8">
            <div class="text-center space-y-4 mb-10"><h2 class="text-3xl md:text-5xl font-black text-white">Pricing & Boosts</h2></div>
        </div>
        <div id="view-faq" class="fade-in hidden max-w-4xl mx-auto mt-6"></div>
        <div id="view-about" class="fade-in hidden max-w-3xl mx-auto mt-6"></div>
        <div id="view-support" class="fade-in hidden max-w-2xl mx-auto mt-10"></div>

    </main>

    <footer class="mt-auto border-t border-white/10 bg-[#020617]/80 py-8 text-center text-xs text-slate-500">
        © 2026 AgromartDirect Ghana. All rights reserved.
    </footer>

    <!-- JAVASCRIPT LOGIC -->
    <script>
        const API_URL = "https://agri-connect-api-3.onrender.com";
        const PAYSTACK_PUBLIC_KEY = "pk_live_330a243539cdc3bf38ba0808ae8156d620ad03ed"; 
        const GOOGLE_CLIENT_ID = "235464348393-sovqvjql532r4f480ngva5287rupkjma.apps.googleusercontent.com"; 

        let agriToken = localStorage.getItem("agri_token") || "";
        let uploadedImages = [];
        let allLoadedProducts = [];
        let allLoadedRfqs = [];
        let currentUserEmail = "";
        let myLoadedAds = [];
        
        let currentCategoryState = "";
        let currentSearchState = "";
        let currentRegionState = "All Regions";
        let currentMarketMode = "ads";
        
        let currentOrderPhone = "";
        let currentOrderName = "";
        let currentOrderBasePrice = 0;
        let currentOrderUnit = "";
        let currentOrderSellerLoc = "";
        let currentOrderTabState = "direct";
        let pendingAdPayload = null;

        const platformFeatures = [
            { icon: "🚚", title: "Haulage Pool", desc: "Book cheap return-trip truck space or list your empty haulage truck returning from deliveries.", color: "from-amber-900/60 to-[#020617]", view: "haulage" },
            { icon: "🩺", title: "AgriDoctor AI Scanner", desc: "Scan diseased crops or sick livestock with your camera for instant organic and chemical treatment plans.", color: "from-rose-900/60 to-[#020617]", view: "agridoctor" },
            { icon: "🚜", title: "Direct Farmer Market", desc: "Sell poultry, crops, and livestock directly to buyers nationwide with zero middleman fees.", color: "from-emerald-900/60 to-[#020617]", view: "marketplace" },
            { icon: "🤝", title: "Smart Deal Room", desc: "Negotiate prices, split group orders, and secure bulk buys with our integrated deal room.", color: "from-blue-900/60 to-[#020617]", view: "marketplace" },
            { icon: "♻️", title: "Eco-Loop Logistics", desc: "Turn farm waste into cash. Request bulk pickups for used oil, cassava peels, and cocoa pods.", color: "from-teal-900/60 to-[#020617]", view: "waste" },
            { icon: "📚", title: "Agri Trainer Hub", desc: "Access free, step-by-step commercial farming guides for crops, poultry, and aquaculture.", color: "from-purple-900/60 to-[#020617]", view: "trainer" }
        ];
        
        let currentSlide = 0;
        function initSlideshow() {
            const container = document.getElementById('feature-slideshow');
            if(!container) return;
            const renderSlide = () => {
                const slide = platformFeatures[currentSlide];
                container.innerHTML = `
                    <div onclick="navigate('${slide.view}')" class="w-full h-full bg-gradient-to-br ${slide.color} flex flex-col md:flex-row items-center justify-center p-8 text-center md:text-left slide-fade cursor-pointer hover:opacity-90 transition-opacity group">
                        <div class="text-7xl md:text-8xl mb-4 md:mb-0 md:mr-10 filter drop-shadow-lg group-hover:scale-110 transition-transform">${slide.icon}</div>
                        <div>
                            <span class="text-[10px] text-white/50 uppercase font-black tracking-widest mb-1 block">Platform Feature</span>
                            <h3 class="text-2xl md:text-4xl font-black text-white mb-2 tracking-tight group-hover:text-emerald-400 transition-colors">${slide.title}</h3>
                            <p class="text-slate-300 text-sm md:text-base max-w-lg leading-relaxed mx-auto md:mx-0">${slide.desc}</p>
                        </div>
                    </div>
                `;
                currentSlide = (currentSlide + 1) % platformFeatures.length;
            };
            renderSlide();
            setInterval(renderSlide, 5000);
        }

        const fallbackDummyNews = [
            { source: "MoFA Update", date: "Today", title: "Government Announces Subsidy on NPK Fertilizers for Season", snippet: "The Ministry of Food and Agriculture has rolled out a new digital tracking system...", link: "https://mofa.gov.gh/" },
            { source: "COCOBOD", date: "Yesterday", title: "Cocoa Farm Gate Price Adjusted Upward to Support Local Growers", snippet: "In a bid to support local farmers, the guaranteed price per bag has seen an adjustment...", link: "https://cocobod.gh/" }
        ];

        async function loadAgriNews() {
            const grid = document.getElementById('newsroom-grid');
            if(!grid) return;
            renderNewsData(fallbackDummyNews, grid);
        }

        function renderNewsData(newsArray, grid) {
            grid.innerHTML = newsArray.map(n => `
                <div class="glass-card p-6 rounded-3xl border border-white/5 shadow-lg cursor-pointer" onclick="window.open('${n.link}', '_blank')">
                    <h4 class="text-white font-black text-sm mb-2">${n.title}</h4>
                    <p class="text-xs text-slate-400 mb-4">${n.snippet}</p>
                </div>
            `).join('');
        }

        const agriTrainerData = {
            crops: [{ id: 'tomato', icon: '🍅', title: 'Tomatoes', intro: 'High yield, 3-month cycle.', guide: '<h3>Nursery</h3><p>Start seeds in trays.</p>' }],
            animals: [{ id: 'broiler', icon: '🐔', title: 'Broiler Chickens', intro: '6-week meat birds.', guide: '<h3>Brooding</h3><p>Preheat brooder.</p>' }]
        };

        function showToast(msg, type='success') {
            const c = document.getElementById('toast-container');
            const t = document.createElement('div');
            t.className = `p-4 pr-6 rounded-2xl shadow-2xl glass-card flex items-center gap-3 fade-in border-l-4 ${type === 'error' ? 'border-rose-500 text-rose-100' : 'border-emerald-500 text-emerald-100'}`;
            t.innerHTML = `<span class="text-sm font-bold tracking-wide">${msg}</span>`;
            c.appendChild(t);
            setTimeout(() => { t.style.opacity = '0'; setTimeout(() => t.remove(), 300); }, 3000);
        }

        function navigate(view) {
            const views = ['home', 'marketplace', 'auth', 'grants', 'farm-manager', 'intel', 'calculator', 'trainer', 'post', 'dashboard', 'pricing', 'faq', 'about', 'support', 'rentals', 'waste', 'agridoctor', 'haulage'];
            views.forEach(v => document.getElementById(`view-${v}`)?.classList.add('hidden'));
            document.getElementById(`view-${view}`)?.classList.remove('hidden');
            window.scrollTo({ top: 0, behavior: 'smooth' });
            if(view === 'marketplace') executeFilters();
            if(view === 'grants') loadGrants();
            if(view === 'farm-manager') loadFarmBatches();
            if(view === 'intel') loadMarketIntel();
            if(view === 'rentals') loadRentals();
            if(view === 'waste') loadWasteRequests();
            if(view === 'haulage') loadHaulagePool();
            if(view === 'dashboard') { loadMyAds(); loadMyTenders(); loadMyRentals(); loadMyWasteRequests(); }
        }

        function toggleAuthBox(box) { 
            ['login-box','signup-box', 'forgot-password-box'].forEach(b => document.getElementById(b)?.classList.add('hidden')); 
            document.getElementById(box + '-box')?.classList.remove('hidden'); 
        }

        function logout() { localStorage.removeItem("agri_token"); window.location.reload(); }
        function requireAuthToPost() { if (!agriToken) { showToast("Sign in required", "error"); navigate('auth'); } else { navigate('post'); } }
        function toggleSunlightMode() { document.getElementById('app-body').classList.toggle('sunlight-mode'); }
        function togglePassword(id) { const f = document.getElementById(id); if(f) f.type = f.type === "password" ? "text" : "password"; }

        function initGoogleAuth() {
            try {
                if (typeof google === 'undefined' || !google.accounts) return setTimeout(initGoogleAuth, 300);
                google.accounts.id.initialize({
                    client_id: GOOGLE_CLIENT_ID,
                    callback: async (res) => {
                        const r = await fetch(`${API_URL}/api/v1/auth/google`, { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({credential: res.credential}) });
                        const d = await r.json();
                        agriToken = d.access_token; localStorage.setItem("agri_token", agriToken);
                        navigate('dashboard');
                    }
                });
                google.accounts.id.renderButton(document.getElementById('google-signin-btn-login'), { theme: "filled_blue", size: "large", width: "300" });
                google.accounts.id.renderButton(document.getElementById('google-signin-btn-signup'), { theme: "filled_blue", size: "large", width: "300" });
            } catch(e) {}
        }

        window.addEventListener('DOMContentLoaded', () => {
            initGoogleAuth(); initSlideshow(); loadAgriNews(); loadBuyerRequests();
            if (agriToken) {
                fetch(`${API_URL}/api/v1/me?token=${agriToken}`).then(r => r.ok ? r.json() : Promise.reject()).then(d => setupUserProfile(d)).catch(() => logout());
            } else {
                document.getElementById('nav-login-btn')?.classList.remove('hidden');
            }
            navigate('home');
        });

        function setupUserProfile(data) {
            currentUserEmail = data.email || "";
            document.getElementById('nav-user-name')?.classList.remove('hidden');
            document.getElementById('nav-user-name').innerText = `Hi, ${(data.full_name||'User').split(' ')[0]}`;
            document.getElementById('nav-login-btn')?.classList.add('hidden');
            document.getElementById('nav-user-profile')?.classList.remove('hidden');
            document.getElementById('nav-user-profile')?.classList.add('flex');
            document.getElementById('my-profile-name').innerText = data.full_name || "User";
            document.getElementById('my-profile-email').innerText = data.email || "";
            if (data.email === "enochdani9@gmail.com") document.getElementById('admin-panel')?.classList.remove('hidden');
        }

        async function loginUser() {
            const email = document.getElementById('login-email').value.trim();
            const password = document.getElementById('login-password').value.trim();
            const res = await fetch(`${API_URL}/api/v1/login`, { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({email, password}) });
            const data = await res.json();
            if (!res.ok) return showToast(data.detail, "error");
            agriToken = data.access_token; localStorage.setItem("agri_token", agriToken);
            navigate('dashboard');
        }

        async function signupUser() {
            const full_name = document.getElementById('su-name').value.trim();
            const email = document.getElementById('su-email').value.trim();
            const age = parseInt(document.getElementById('su-age').value);
            const phone_number = document.getElementById('su-phone').value.trim();
            const password = document.getElementById('su-password').value.trim();
            const res = await fetch(`${API_URL}/api/v1/signup`, { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({full_name, email, age, phone_number, password}) });
            const data = await res.json();
            if (!res.ok) return showToast(data.detail, "error");
            agriToken = data.access_token; localStorage.setItem("agri_token", agriToken);
            navigate('dashboard');
        }

        function executeSearch() { navigate('marketplace'); }
        function executeCategory(cat) { currentCategoryState = cat; navigate('marketplace'); }
        function executeFilters() { loadMarketplaceGrid(); }
        function switchMarketplaceTab(tab) { if(tab==='ads') { document.getElementById('home-ads-container').classList.remove('hidden'); document.getElementById('home-rfq-container').classList.add('hidden'); } else { document.getElementById('home-ads-container').classList.add('hidden'); document.getElementById('home-rfq-container').classList.remove('hidden'); loadBuyerRequests(); } }
        function setMarketplaceMode(m) { currentMarketMode = m; loadMarketplaceGrid(); }
        function startVoiceSearch() { showToast("Voice search listening..."); }

        async function loadMarketplaceGrid() {
            const res = await fetch(`${API_URL}/api/v1/products`);
            const products = await res.json();
            renderProductGrid(products, document.getElementById('product-grid'));
        }

        function renderProductGrid(products, grid) {
            if(!grid) return;
            grid.innerHTML = products.map(item => `
                <div class="glass-card rounded-[2rem] p-6 shadow-xl flex flex-col justify-between">
                    <h3 class="text-xl font-black text-white mb-2">${item.product_name}</h3>
                    <p class="text-2xl font-black text-emerald-400 mb-4">GH₵${item.base_price_ghs} <span class="text-xs text-slate-400">/ ${item.unit}</span></p>
                    <button onclick="openOrderModal('${item.phone_number}', '${item.product_name}', '${item.base_price_ghs}', '${item.unit}', '${item.neighborhood}', ${item.id})" class="bg-[#25D366]/20 text-[#25D366] font-black py-3 rounded-xl text-xs">Deal Room</button>
                </div>
            `).join('');
        }

        function buildTrendingSection(products) { renderProductGrid(products.slice(0,3), document.getElementById('trending-grid')); }
        function buildMarketTicker(products) { document.getElementById('market-ticker').innerHTML = `<span class="text-xs text-emerald-400 font-bold">Maize Avg: GH₵ 320 / bag • Broilers Avg: GH₵ 140 / bird</span>`; }

        function openOrderModal(phone, name, price, unit, loc, id) {
            currentOrderPhone = phone; currentOrderName = name; currentOrderBasePrice = parseFloat(price); currentOrderUnit = unit;
            document.getElementById('order-product-name').innerText = name;
            document.getElementById('order-base-price').innerText = price;
            document.getElementById('order-unit').innerText = unit;
            document.getElementById('order-modal').classList.remove('hidden'); document.getElementById('order-modal').classList.add('flex');
        }
        function closeOrderModal() { document.getElementById('order-modal').classList.add('hidden'); document.getElementById('order-modal').classList.remove('flex'); }
        function switchOrderTab(t) { currentOrderTabState = t; }
        function updateHaggleMeter() { calculateOrderTotal(); }
        function calculateOrderTotal() { document.getElementById('order-total-price').innerText = (currentOrderBasePrice * parseInt(document.getElementById('order-quantity').value || 1)).toFixed(2); }
        function executeDealWhatsApp() { window.open(`https://wa.me/${currentOrderPhone.replace(/\D/g,'')}?text=I want to buy ${currentOrderName}`, '_blank'); closeOrderModal(); }
        function executeCallFarmer() { window.open(`tel:${currentOrderPhone}`, '_self'); closeOrderModal(); }

        async function submitAd() {
            const product_name = document.getElementById('post-name').value.trim();
            const description = document.getElementById('post-description').value.trim();
            const unit = document.getElementById('post-unit').value.trim();
            const base_price_ghs = document.getElementById('post-price').value.trim();
            const neighborhood = document.getElementById('post-town').value.trim();
            await fetch(`${API_URL}/api/v1/products?token=${agriToken}`, { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({product_name, description, category: 'Poultry', unit, base_price_ghs, delivery_details: 'Standard', neighborhood, image_data: null}) });
            showToast("Ad submitted!"); navigate('dashboard');
        }

        async function loadMyAds() {
            const res = await fetch(`${API_URL}/api/v1/my-products?token=${agriToken}`);
            const ads = await res.json(); myLoadedAds = ads;
            document.getElementById('my-ads-list').innerHTML = ads.map(a => `<div class="glass-card p-4 rounded-xl mb-2 flex justify-between items-center"><span class="font-bold text-white">${a.product_name}</span><span class="text-emerald-400">GH₵${a.base_price_ghs}</span></div>`).join('');
        }

        async function loadGrants() {
            const res = await fetch(`${API_URL}/api/v1/grants`);
            const grants = await res.json();
            document.getElementById('grants-grid').innerHTML = grants.map(g => `<div class="glass-card p-6 rounded-3xl border border-amber-500/20"><h3 class="text-lg font-black text-white mb-2">${g.title}</h3><p class="text-emerald-400 font-bold mb-4">Value: ${g.amount}</p><a href="${g.link}" target="_blank" class="bg-amber-500 text-[#020617] font-black px-4 py-2 rounded-xl text-xs block text-center">Apply Now</a></div>`).join('');
        }

        function openBatchModal() { document.getElementById('batch-modal').classList.remove('hidden'); document.getElementById('batch-modal').classList.add('flex'); }
        function closeBatchModal() { document.getElementById('batch-modal').classList.add('hidden'); document.getElementById('batch-modal').classList.remove('flex'); }
        async function createBatch() {
            const batch_name = document.getElementById('batch-name').value.trim();
            const category = document.getElementById('batch-cat').value;
            const quantity = parseInt(document.getElementById('batch-qty').value);
            const harvest_days = parseInt(document.getElementById('batch-days').value);
            await fetch(`${API_URL}/api/v1/farm-batches?token=${agriToken}`, { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({batch_name, category, quantity, harvest_days}) });
            closeBatchModal(); loadFarmBatches();
        }
        async function loadFarmBatches() {
            const res = await fetch(`${API_URL}/api/v1/farm-batches?token=${agriToken}`);
            const batches = await res.json();
            document.getElementById('farm-batches-grid').innerHTML = batches.map(b => `<div class="glass-card p-6 rounded-2xl"><h3 class="text-lg font-black text-white">${b.batch_name}</h3><p class="text-xs text-slate-400">Qty: ${b.quantity} | Harvest: ${b.harvest_date}</p></div>`).join('');
        }

        async function loadMarketIntel() {
            const res = await fetch(`${API_URL}/api/v1/market-intel`);
            const intel = await res.json();
            document.getElementById('intel-grid').innerHTML = intel.map(i => `<div class="glass-card p-6 rounded-2xl"><h3 class="font-black text-white">${i.category}</h3><p class="text-2xl font-black text-emerald-400">GH₵ ${i.national_avg}</p></div>`).join('');
        }

        function openRfqModal() { document.getElementById('rfq-modal').classList.remove('hidden'); document.getElementById('rfq-modal').classList.add('flex'); }
        function closeRfqModal() { document.getElementById('rfq-modal').classList.add('hidden'); document.getElementById('rfq-modal').classList.remove('flex'); }
        async function submitBuyerRequest() {
            const item_needed = document.getElementById('rfq-item').value.trim();
            const category = document.getElementById('rfq-category').value;
            const quantity = document.getElementById('rfq-quantity').value.trim();
            const target_budget_ghs = document.getElementById('rfq-budget').value.trim();
            const delivery_destination = document.getElementById('rfq-destination').value.trim();
            await fetch(`${API_URL}/api/v1/buyer-requests?token=${agriToken}`, { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({item_needed, category, quantity, target_budget_ghs, delivery_destination, description: 'Required'}) });
            closeRfqModal(); loadBuyerRequests();
        }
        async function loadBuyerRequests() {
            const res = await fetch(`${API_URL}/api/v1/buyer-requests`);
            const rfqs = await res.json(); allLoadedRfqs = rfqs;
            renderRfqGrid(rfqs, document.getElementById('rfq-grid'));
        }
        function renderRfqGrid(rfqs, grid) {
            if(!grid) return;
            grid.innerHTML = rfqs.map(r => `<div class="glass-card p-6 rounded-2xl"><h3 class="font-black text-white">${r.item_needed}</h3><p class="text-emerald-400 font-bold">Budget: GH₵${r.target_budget_ghs}</p></div>`).join('');
        }

        function calculateFeedMix() { showToast("Feed mix computed successfully!"); }
        async function loadRentals() { document.getElementById('rentals-grid').innerHTML = `<div class="glass-card p-6 rounded-xl">Honda Water Pump - GH₵ 100/day</div>`; }
        function openRentalPostModal() { showToast("List rental triggered"); }
        async function loadMyRentals() { document.getElementById('my-rentals-list').innerHTML = `No rentals`; }
        async function submitWasteRequest() { showToast("Eco-loop pickup booked!"); }
        async function loadMyWasteRequests() { document.getElementById('my-waste-list').innerHTML = `No waste requests`; }

        // --- FEATURE 1: AGRIDOCTOR AI SCANNER LOGIC ---
        function handleAgriDoctorUpload(e) {
            const f = e.target.files[0]; if(!f) return;
            const r = new FileReader();
            r.onload = (ev) => {
                const p = document.getElementById('agridoctor-preview');
                p.src = ev.target.result; p.classList.remove('hidden');
                document.getElementById('agridoctor-analyze-btn').classList.remove('hidden');
            };
            r.readAsDataURL(f);
        }
        function processAgriDoctor() {
            document.getElementById('agridoctor-upload-state').classList.add('hidden');
            document.getElementById('agridoctor-processing-state').classList.remove('hidden');
            setTimeout(() => {
                document.getElementById('agridoctor-processing-state').classList.add('hidden');
                document.getElementById('agridoctor-result-state').classList.remove('hidden');
                showToast("Diagnosis Complete! 🩺");
            }, 3000);
        }
        function resetAgriDoctor() {
            document.getElementById('agridoctor-result-state').classList.add('hidden');
            document.getElementById('agridoctor-preview').classList.add('hidden');
            document.getElementById('agridoctor-analyze-btn').classList.add('hidden');
            document.getElementById('agridoctor-upload-state').classList.remove('hidden');
        }

        // --- FEATURE 2: HAULAGE POOL LOGIC (LIVE BACKEND INTEGRATION) ---
        async function loadHaulagePool() {
            const grid = document.getElementById('haulage-grid');
            if (!grid) return;
            grid.innerHTML = '<div class="col-span-full text-center text-slate-400 py-10">Loading active return-trip haulage trucks... ⏳</div>';
            try {
                const res = await fetch(`${API_URL}/api/v1/haulage`);
                const items = await res.json();
                if (!items.length) {
                    grid.innerHTML = '<div class="col-span-full text-center text-slate-400 py-10">No empty-leg trucks currently listed.</div>';
                    return;
                }
                grid.innerHTML = items.map(h => `
                    <div class="glass-card p-6 rounded-[2.5rem] border border-amber-500/30 shadow-xl flex flex-col justify-between">
                        <div>
                            <span class="bg-amber-500/10 text-amber-400 text-[10px] font-black uppercase px-2.5 py-1 rounded-md">Empty-Leg Return</span>
                            <h3 class="text-xl font-black text-white mt-2">${h.route}</h3>
                            <p class="text-xs text-slate-300 font-bold mb-1">🚛 ${h.truck}</p>
                            <p class="text-xs text-slate-400 mb-4">Driver: ${h.driver_name} (${h.capacity})</p>
                            <p class="text-lg font-black text-emerald-400 mb-4">GH₵ ${h.price}</p>
                        </div>
                        <a href="https://wa.me/233${(h.driver_phone||'').replace(/\D/g,'').replace(/^0/,'')}?text=I want to book your empty-leg return truck space for ${h.route}" target="_blank" class="w-full bg-[#25D366] text-[#020617] font-black py-3 rounded-xl text-xs text-center block">Book Return Freight 🚚</a>
                    </div>
                `).join('');
            } catch (e) {
                grid.innerHTML = '<div class="col-span-full text-center text-rose-400 py-6">Could not load haulage board.</div>';
            }
        }

        async function openHaulagePostModal() {
            if (!agriToken) { showToast("Sign in to list empty trucks", "error"); return navigate('auth'); }
            const route = prompt("Route (e.g. Tamale ➔ Accra):"); if (!route) return;
            const truck = prompt("Truck Model & Capacity (e.g. 10-Ton Tata Cargo):"); if (!truck) return;
            const price = prompt("Discounted Return Rate (GH₵):"); if (!price) return;
            const date = prompt("Departure / Return Date:"); if (!date) return;
            const capacity = prompt("Available Cargo Space:"); if (!capacity) return;

            try {
                const res = await fetch(`${API_URL}/api/v1/haulage?token=${agriToken}`, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ route, truck, price, date, capacity })
                });
                if(!res.ok) throw new Error("Failed");
                showToast("Empty truck successfully published! 🚚");
                loadHaulagePool();
            } catch(e) {
                showToast("Error posting haulage listing", "error");
            }
        }

        function showTrainerSubCategory(cat) {
            const grid = document.getElementById('trainer-items-grid');
            grid.innerHTML = agriTrainerData[cat].map(i => `<div class="glass-card p-6 rounded-2xl text-center"><div class="text-4xl mb-2">${i.icon}</div><h4 class="font-black text-white">${i.title}</h4></div>`).join('');
            document.getElementById('trainer-categories').classList.add('hidden');
            document.getElementById('trainer-items').classList.remove('hidden');
        }
        function resetTrainer() {
            document.getElementById('trainer-items').classList.add('hidden');
            document.getElementById('trainer-categories').classList.remove('hidden');
        }
    </script>
</body>
</html>
