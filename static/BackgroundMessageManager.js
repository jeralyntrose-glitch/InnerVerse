/**
 * Background Message Manager
 * 
 * Manages background message processing for PWA - allows AI responses to continue
 * processing when the user closes/switches away from the app.
 * 
 * Features:
 * - IndexedDB persistence for job tracking across sessions
 * - Graceful fallback to in-memory storage if IndexedDB fails
 * - Resume detection (visibilitychange, focus events)
 * - Exponential backoff polling (3s, 6s, 12s)
 * - Timeout handling (5 minutes max)
 * - Error recovery with automatic retry
 */

class BackgroundMessageManager {
    constructor() {
        this.dbName = 'innerverse_bg_jobs';
        this.storeName = 'pending_jobs';
        this.db = null;
        this.inMemoryJobs = new Map(); // Fallback if IndexedDB fails
        this.useIndexedDB = true;
        this.pollingIntervals = new Map(); // Track active polling timers
        this.maxPollTime = 5 * 60 * 1000; // 5 minutes
        
        this.initDB();
    }
    
    /**
     * Initialize IndexedDB with graceful fallback
     */
    async initDB() {
        try {
            const request = indexedDB.open(this.dbName, 1);
            
            request.onerror = () => {
                console.warn('⚠️ IndexedDB not available, using in-memory storage');
                this.useIndexedDB = false;
            };
            
            request.onsuccess = (event) => {
                this.db = event.target.result;
                console.log('✅ IndexedDB initialized successfully');
            };
            
            request.onupgradeneeded = (event) => {
                const db = event.target.result;
                
                if (!db.objectStoreNames.contains(this.storeName)) {
                    const objectStore = db.createObjectStore(this.storeName, { keyPath: 'jobId' });
                    objectStore.createIndex('conversationId', 'conversationId', { unique: false });
                    objectStore.createIndex('lessonId', 'lessonId', { unique: false });
                    objectStore.createIndex('status', 'status', { unique: false });
                    console.log('📦 IndexedDB object store created');
                }
            };
        } catch (error) {
            console.warn('⚠️ IndexedDB initialization failed:', error);
            this.useIndexedDB = false;
        }
    }
    
    /**
     * Save a pending job
     */
    async saveJob(jobData) {
        const job = {
            jobId: jobData.jobId,
            conversationId: jobData.conversationId || null,
            lessonId: jobData.lessonId || null,
            status: 'pending',
            createdAt: Date.now(),
            pollAttempts: 0
        };
        
        if (this.useIndexedDB && this.db) {
            try {
                await this._saveToIndexedDB(job);
                console.log(`💾 Job ${job.jobId} saved to IndexedDB`);
            } catch (error) {
                console.warn('⚠️ IndexedDB save failed, using in-memory:', error);
                this.inMemoryJobs.set(job.jobId, job);
            }
        } else {
            this.inMemoryJobs.set(job.jobId, job);
            console.log(`💾 Job ${job.jobId} saved to in-memory storage`);
        }
        
        return job;
    }
    
    /**
     * Get a job by ID
     */
    async getJob(jobId) {
        if (this.useIndexedDB && this.db) {
            try {
                return await this._getFromIndexedDB(jobId);
            } catch (error) {
                console.warn('⚠️ IndexedDB get failed, checking in-memory:', error);
                return this.inMemoryJobs.get(jobId);
            }
        } else {
            return this.inMemoryJobs.get(jobId);
        }
    }
    
    /**
     * Get all pending jobs
     */
    async getPendingJobs(conversationId = null, lessonId = null) {
        if (this.useIndexedDB && this.db) {
            try {
                return await this._getAllPendingFromIndexedDB(conversationId, lessonId);
            } catch (error) {
                console.warn('⚠️ IndexedDB getAll failed, using in-memory:', error);
                return Array.from(this.inMemoryJobs.values()).filter(job => {
                    if (conversationId && job.conversationId !== conversationId) return false;
                    if (lessonId && job.lessonId !== lessonId) return false;
                    return job.status === 'pending';
                });
            }
        } else {
            return Array.from(this.inMemoryJobs.values()).filter(job => {
                if (conversationId && job.conversationId !== conversationId) return false;
                if (lessonId && job.lessonId !== lessonId) return false;
                return job.status === 'pending';
            });
        }
    }
    
    /**
     * Update job status
     */
    async updateJobStatus(jobId, status) {
        const job = await this.getJob(jobId);
        if (!job) {
            console.warn(`⚠️ Job ${jobId} not found`);
            return false;
        }
        
        job.status = status;
        job.updatedAt = Date.now();
        
        if (this.useIndexedDB && this.db) {
            try {
                await this._saveToIndexedDB(job);
            } catch (error) {
                console.warn('⚠️ IndexedDB update failed, using in-memory:', error);
                this.inMemoryJobs.set(jobId, job);
            }
        } else {
            this.inMemoryJobs.set(jobId, job);
        }
        
        return true;
    }
    
    /**
     * Delete a job
     */
    async deleteJob(jobId) {
        if (this.useIndexedDB && this.db) {
            try {
                await this._deleteFromIndexedDB(jobId);
            } catch (error) {
                console.warn('⚠️ IndexedDB delete failed:', error);
            }
        }
        
        this.inMemoryJobs.delete(jobId);
        
        // Clear polling timer if exists
        if (this.pollingIntervals.has(jobId)) {
            clearInterval(this.pollingIntervals.get(jobId));
            this.pollingIntervals.delete(jobId);
        }
        
        console.log(`🗑️ Job ${jobId} deleted`);
    }
    
    /**
     * Start polling for a job's completion
     */
    startPolling(jobId, onComplete, onError) {
        let pollAttempts = 0;
        const maxAttempts = 10;
        const startTime = Date.now();
        
        const poll = async () => {
            pollAttempts++;
            
            // Check timeout (5 minutes)
            if (Date.now() - startTime > this.maxPollTime) {
                console.warn(`⏱️ Job ${jobId} polling timeout after 5 minutes`);
                this.stopPolling(jobId);
                if (onError) onError(new Error('Polling timeout'));
                return;
            }
            
            try {
                const response = await fetch(`/api/jobs/${jobId}/status`);
                const data = await response.json();
                
                if (data.success && data.job) {
                    const job = data.job;
                    
                    if (job.status === 'completed') {
                        console.log(`✅ Job ${jobId} completed!`);
                        this.stopPolling(jobId);
                        await this.deleteJob(jobId);
                        if (onComplete) onComplete(job.response_content);
                    } else if (job.status === 'failed') {
                        console.error(`❌ Job ${jobId} failed:`, job.error_message);
                        this.stopPolling(jobId);
                        await this.deleteJob(jobId);
                        if (onError) onError(new Error(job.error_message || 'Job failed'));
                    } else if (job.status === 'processing' || job.status === 'queued') {
                        // Still processing, continue polling
                        console.log(`⏳ Job ${jobId} still ${job.status}, poll attempt ${pollAttempts}`);
                        
                        // Update poll attempts in storage
                        await this.updateJobStatus(jobId, 'pending');
                    }
                }
            } catch (error) {
                console.error(`❌ Error polling job ${jobId}:`, error);
                
                // Don't stop polling on network errors, just log and continue
                if (pollAttempts >= maxAttempts) {
                    this.stopPolling(jobId);
                    if (onError) onError(error);
                }
            }
        };
        
        // Initial poll immediately
        poll();
        
        // Exponential backoff: 3s, 6s, 12s, then 12s interval
        let interval = 3000;
        const timer = setInterval(() => {
            poll();
            if (interval < 12000) {
                clearInterval(timer);
                interval = Math.min(interval * 2, 12000);
                this.pollingIntervals.set(jobId, setInterval(poll, interval));
            }
        }, interval);
        
        this.pollingIntervals.set(jobId, timer);
    }
    
    /**
     * Stop polling for a job
     */
    stopPolling(jobId) {
        if (this.pollingIntervals.has(jobId)) {
            clearInterval(this.pollingIntervals.get(jobId));
            this.pollingIntervals.delete(jobId);
            console.log(`⏸️ Stopped polling job ${jobId}`);
        }
    }
    
    /**
     * Check for pending jobs on app resume
     */
    async checkPendingJobsOnResume(conversationId = null, lessonId = null, onComplete, onError) {
        console.log('🔍 Checking for pending jobs on app resume...');
        
        const pendingJobs = await this.getPendingJobs(conversationId, lessonId);
        
        if (pendingJobs.length === 0) {
            console.log('✅ No pending jobs found');
            return;
        }
        
        console.log(`📋 Found ${pendingJobs.length} pending job(s), starting polling...`);
        
        for (const job of pendingJobs) {
            this.startPolling(job.jobId, onComplete, onError);
        }
    }
    
    // =========================================================================
    // PRIVATE INDEXEDDB METHODS
    // =========================================================================
    
    _saveToIndexedDB(job) {
        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction([this.storeName], 'readwrite');
            const objectStore = transaction.objectStore(this.storeName);
            const request = objectStore.put(job);
            
            request.onsuccess = () => resolve();
            request.onerror = () => reject(request.error);
        });
    }
    
    _getFromIndexedDB(jobId) {
        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction([this.storeName], 'readonly');
            const objectStore = transaction.objectStore(this.storeName);
            const request = objectStore.get(jobId);
            
            request.onsuccess = () => resolve(request.result);
            request.onerror = () => reject(request.error);
        });
    }
    
    _getAllPendingFromIndexedDB(conversationId, lessonId) {
        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction([this.storeName], 'readonly');
            const objectStore = transaction.objectStore(this.storeName);
            
            let request;
            if (conversationId) {
                const index = objectStore.index('conversationId');
                request = index.getAll(conversationId);
            } else if (lessonId) {
                const index = objectStore.index('lessonId');
                request = index.getAll(lessonId);
            } else {
                request = objectStore.getAll();
            }
            
            request.onsuccess = () => {
                const jobs = request.result.filter(job => job.status === 'pending');
                resolve(jobs);
            };
            request.onerror = () => reject(request.error);
        });
    }
    
    _deleteFromIndexedDB(jobId) {
        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction([this.storeName], 'readwrite');
            const objectStore = transaction.objectStore(this.storeName);
            const request = objectStore.delete(jobId);
            
            request.onsuccess = () => resolve();
            request.onerror = () => reject(request.error);
        });
    }
}

// Export for use in other modules
window.BackgroundMessageManager = BackgroundMessageManager;
