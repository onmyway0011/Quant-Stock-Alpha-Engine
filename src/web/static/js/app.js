// 量化股票交易系统 - 前端应用脚本

// 全局配置
const APP_CONFIG = {
    apiBaseUrl: '',
    refreshInterval: 30000, // 30秒
    maxRetries: 3,
    retryDelay: 1000 // 1秒
};

// 全局状态
const APP_STATE = {
    isConnected: true,
    lastUpdate: null,
    retryCount: 0
};

// 工具函数
const Utils = {
    // 格式化时间
    formatTime(timestamp) {
        if (!timestamp) return 'N/A';
        const date = new Date(timestamp);
        return date.toLocaleString('zh-CN', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
        });
    },

    // 格式化金额
    formatCurrency(amount) {
        if (typeof amount !== 'number') return '¥0.00';
        return '¥' + amount.toLocaleString('zh-CN', {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        });
    },

    // 格式化百分比
    formatPercent(value) {
        if (typeof value !== 'number') return '0.00%';
        return (value * 100).toFixed(2) + '%';
    },

    // 防抖函数
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    },

    // 节流函数
    throttle(func, limit) {
        let inThrottle;
        return function() {
            const args = arguments;
            const context = this;
            if (!inThrottle) {
                func.apply(context, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        };
    },

    // 深拷贝
    deepClone(obj) {
        if (obj === null || typeof obj !== 'object') return obj;
        if (obj instanceof Date) return new Date(obj.getTime());
        if (obj instanceof Array) return obj.map(item => this.deepClone(item));
        if (typeof obj === 'object') {
            const clonedObj = {};
            for (const key in obj) {
                if (obj.hasOwnProperty(key)) {
                    clonedObj[key] = this.deepClone(obj[key]);
                }
            }
            return clonedObj;
        }
    },

    // 生成UUID
    generateUUID() {
        return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
            const r = Math.random() * 16 | 0;
            const v = c == 'x' ? r : (r & 0x3 | 0x8);
            return v.toString(16);
        });
    }
};

// API 请求封装
const API = {
    // 基础请求方法
    async request(url, options = {}) {
        const defaultOptions = {
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            },
            timeout: 10000
        };

        const finalOptions = { ...defaultOptions, ...options };

        try {
            const response = await axios(url, finalOptions);
            APP_STATE.isConnected = true;
            APP_STATE.retryCount = 0;
            APP_STATE.lastUpdate = new Date();
            return response.data;
        } catch (error) {
            APP_STATE.isConnected = false;
            console.error('API请求失败:', error);
            
            // 自动重试
            if (APP_STATE.retryCount < APP_CONFIG.maxRetries) {
                APP_STATE.retryCount++;
                await new Promise(resolve => setTimeout(resolve, APP_CONFIG.retryDelay));
                return this.request(url, options);
            }
            
            throw error;
        }
    },

    // GET 请求
    get(url, params = {}) {
        return this.request(url, {
            method: 'GET',
            params
        });
    },

    // POST 请求
    post(url, data = {}) {
        return this.request(url, {
            method: 'POST',
            data
        });
    },

    // PUT 请求
    put(url, data = {}) {
        return this.request(url, {
            method: 'PUT',
            data
        });
    },

    // DELETE 请求
    delete(url) {
        return this.request(url, {
            method: 'DELETE'
        });
    }
};

// 通知系统
const Notification = {
    // 显示成功消息
    success(message, duration = 3000) {
        this.show(message, 'success', duration);
    },

    // 显示错误消息
    error(message, duration = 5000) {
        this.show(message, 'danger', duration);
    },

    // 显示警告消息
    warning(message, duration = 4000) {
        this.show(message, 'warning', duration);
    },

    // 显示信息消息
    info(message, duration = 3000) {
        this.show(message, 'info', duration);
    },

    // 显示通知
    show(message, type = 'info', duration = 3000) {
        const alertId = Utils.generateUUID();
        const alertHtml = `
            <div id="${alertId}" class="alert alert-${type} alert-dismissible fade show" role="alert">
                <i class="bi bi-${this.getIcon(type)}"></i>
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        `;

        // 查找或创建通知容器
        let container = document.getElementById('notification-container');
        if (!container) {
            container = document.createElement('div');
            container.id = 'notification-container';
            container.style.cssText = `
                position: fixed;
                top: 20px;
                right: 20px;
                z-index: 9999;
                max-width: 400px;
            `;
            document.body.appendChild(container);
        }

        container.insertAdjacentHTML('beforeend', alertHtml);

        // 自动移除
        if (duration > 0) {
            setTimeout(() => {
                const alert = document.getElementById(alertId);
                if (alert) {
                    const bsAlert = new bootstrap.Alert(alert);
                    bsAlert.close();
                }
            }, duration);
        }
    },

    // 获取图标
    getIcon(type) {
        const icons = {
            success: 'check-circle',
            danger: 'exclamation-triangle',
            warning: 'exclamation-triangle',
            info: 'info-circle'
        };
        return icons[type] || 'info-circle';
    }
};

// 加载状态管理
const Loading = {
    // 显示加载状态
    show(target, message = '加载中...') {
        const element = typeof target === 'string' ? document.getElementById(target) : target;
        if (!element) return;

        const loadingHtml = `
            <div class="d-flex justify-content-center align-items-center p-4">
                <div class="loading me-2"></div>
                <span>${message}</span>
            </div>
        `;

        element.innerHTML = loadingHtml;
    },

    // 隐藏加载状态
    hide(target) {
        const element = typeof target === 'string' ? document.getElementById(target) : target;
        if (!element) return;

        const loadingElement = element.querySelector('.loading');
        if (loadingElement) {
            loadingElement.parentElement.remove();
        }
    }
};

// 表单验证
const Validator = {
    // 验证规则
    rules: {
        required: (value) => value !== null && value !== undefined && value !== '',
        email: (value) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value),
        url: (value) => /^https?:\/\/.+/.test(value),
        number: (value) => !isNaN(value) && isFinite(value),
        min: (value, min) => parseFloat(value) >= min,
        max: (value, max) => parseFloat(value) <= max,
        minLength: (value, length) => value.length >= length,
        maxLength: (value, length) => value.length <= length
    },

    // 验证字段
    validateField(value, rules) {
        const errors = [];
        
        for (const rule of rules) {
            if (typeof rule === 'string') {
                if (!this.rules[rule](value)) {
                    errors.push(this.getErrorMessage(rule));
                }
            } else if (typeof rule === 'object') {
                const { name, params } = rule;
                if (!this.rules[name](value, ...params)) {
                    errors.push(this.getErrorMessage(name, params));
                }
            }
        }
        
        return errors;
    },

    // 获取错误消息
    getErrorMessage(rule, params = []) {
        const messages = {
            required: '此字段为必填项',
            email: '请输入有效的邮箱地址',
            url: '请输入有效的URL',
            number: '请输入有效的数字',
            min: `值不能小于 ${params[0]}`,
            max: `值不能大于 ${params[0]}`,
            minLength: `长度不能少于 ${params[0]} 个字符`,
            maxLength: `长度不能超过 ${params[0]} 个字符`
        };
        return messages[rule] || '输入无效';
    },

    // 验证表单
    validateForm(formElement, schema) {
        const errors = {};
        const formData = new FormData(formElement);
        
        for (const [fieldName, rules] of Object.entries(schema)) {
            const value = formData.get(fieldName);
            const fieldErrors = this.validateField(value, rules);
            
            if (fieldErrors.length > 0) {
                errors[fieldName] = fieldErrors;
            }
        }
        
        return errors;
    }
};

// 本地存储管理
const Storage = {
    // 设置项
    set(key, value) {
        try {
            localStorage.setItem(key, JSON.stringify(value));
        } catch (error) {
            console.error('存储数据失败:', error);
        }
    },

    // 获取项
    get(key, defaultValue = null) {
        try {
            const item = localStorage.getItem(key);
            return item ? JSON.parse(item) : defaultValue;
        } catch (error) {
            console.error('读取数据失败:', error);
            return defaultValue;
        }
    },

    // 移除项
    remove(key) {
        try {
            localStorage.removeItem(key);
        } catch (error) {
            console.error('删除数据失败:', error);
        }
    },

    // 清空
    clear() {
        try {
            localStorage.clear();
        } catch (error) {
            console.error('清空数据失败:', error);
        }
    }
};

// 事件管理器
const EventManager = {
    events: {},

    // 注册事件
    on(event, callback) {
        if (!this.events[event]) {
            this.events[event] = [];
        }
        this.events[event].push(callback);
    },

    // 移除事件
    off(event, callback) {
        if (!this.events[event]) return;
        
        const index = this.events[event].indexOf(callback);
        if (index > -1) {
            this.events[event].splice(index, 1);
        }
    },

    // 触发事件
    emit(event, data) {
        if (!this.events[event]) return;
        
        this.events[event].forEach(callback => {
            try {
                callback(data);
            } catch (error) {
                console.error('事件回调执行失败:', error);
            }
        });
    }
};

// 系统状态监控
const SystemMonitor = {
    interval: null,
    
    // 开始监控
    start() {
        this.interval = setInterval(() => {
            this.checkSystemStatus();
        }, APP_CONFIG.refreshInterval);
    },

    // 停止监控
    stop() {
        if (this.interval) {
            clearInterval(this.interval);
            this.interval = null;
        }
    },

    // 检查系统状态
    async checkSystemStatus() {
        try {
            const status = await API.get('/api/system/status');
            this.updateStatusIndicators(status);
            EventManager.emit('systemStatusUpdate', status);
        } catch (error) {
            console.error('获取系统状态失败:', error);
            this.updateStatusIndicators({ healthy: false });
        }
    },

    // 更新状态指示器
    updateStatusIndicators(status) {
        const indicators = document.querySelectorAll('.status-indicator');
        indicators.forEach(indicator => {
            if (status.healthy) {
                indicator.className = 'status-indicator status-running';
            } else {
                indicator.className = 'status-indicator status-stopped';
            }
        });

        // 更新导航栏状态
        const navStatus = document.querySelector('.navbar-text');
        if (navStatus) {
            if (status.healthy) {
                navStatus.innerHTML = '<i class="bi bi-circle-fill text-success"></i> 系统运行中';
            } else {
                navStatus.innerHTML = '<i class="bi bi-circle-fill text-danger"></i> 系统异常';
            }
        }
    }
};

// 页面初始化
document.addEventListener('DOMContentLoaded', function() {
    // 初始化工具提示
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // 初始化弹出框
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });

    // 开始系统监控
    SystemMonitor.start();

    // 监听页面卸载
    window.addEventListener('beforeunload', function() {
        SystemMonitor.stop();
    });

    // 监听网络状态
    window.addEventListener('online', function() {
        APP_STATE.isConnected = true;
        Notification.success('网络连接已恢复');
    });

    window.addEventListener('offline', function() {
        APP_STATE.isConnected = false;
        Notification.warning('网络连接已断开');
    });
});

// 导出到全局
window.Utils = Utils;
window.API = API;
window.Notification = Notification;
window.Loading = Loading;
window.Validator = Validator;
window.Storage = Storage;
window.EventManager = EventManager;
window.SystemMonitor = SystemMonitor;