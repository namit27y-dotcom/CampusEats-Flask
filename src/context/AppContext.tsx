import React, { createContext, useContext, useState, useEffect, useCallback, useMemo, useRef } from 'react';
import {
  UserRole,
  UserProfile,
  Canteen,
  MenuItem,
  CartItem,
  Order,
  OrderStatus,
  InventoryItem,
  PickupSlot,
  AppNotification,
  OrderFeedback,
} from '../types';
import {
  INITIAL_USERS,
  INITIAL_CANTEENS,
  INITIAL_MENU_ITEMS,
  INITIAL_PICKUP_SLOTS,
  INITIAL_ORDERS,
  INITIAL_INVENTORY,
} from '../data/mockData';
import { playOrderPlacedSound, playOrderReadyChime, announceTokenVoice } from '../utils/soundEffects';
import { apiRequest, getApiBaseUrl } from '../utils/api';
import { getFoodImage, DEFAULT_FOOD_IMAGES } from '../utils/foodImages';
import { io } from 'socket.io-client';

interface AppContextType {
  currentRole: UserRole;
  setRole: (role: UserRole) => void;
  currentUser: UserProfile;
  setCurrentUser: (user: UserProfile) => void;
  loginUser: (email: string, password: string) => Promise<UserProfile>;
  registerUser: (name: string, email: string, password: string) => Promise<UserProfile>;
  logoutUser: () => void;
  availableUsers: UserProfile[];
  
  // Canteen
  selectedCanteen: Canteen;
  canteens: Canteen[];
  selectCanteen: (canteenId: string) => void;
  updateCanteen: (canteen: Canteen) => void;

  // Menu & Inventory
  menuItems: MenuItem[];
  updateMenuItem: (item: MenuItem) => void;
  addMenuItem: (item: Omit<MenuItem, 'id'>) => void;
  inventory: InventoryItem[];
  updateInventoryStock: (itemId: string, newStock: number) => void;
  restockItem: (itemId: string, addAmount: number) => void;

  // Cart
  cart: CartItem[];
  cartCount: number;
  cartTotal: number;
  addToCart: (menuItem: MenuItem, quantity?: number, customizations?: Record<string, string>) => void;
  removeFromCart: (cartItemId: string) => void;
  updateCartQuantity: (cartItemId: string, delta: number) => void;
  clearCart: () => void;

  // Slots & Orders
  pickupSlots: PickupSlot[];
  orders: Order[];
  activeOrders: Order[];
  activeOrder: Order | null; // latest active order for current student
  placeOrder: (pickupSlot: string, paymentMethod: 'upi' | 'wallet' | 'card' | 'cash') => Promise<Order>;
  cancelOrder: (orderId: string) => boolean;
  updateOrderStatus: (orderId: string, newStatus: OrderStatus) => void;
  callToken: (orderId: string) => void;
  verifyAndCollectOrder: (tokenOrId: string) => Promise<{ success: boolean; message: string; order?: Order }>;
  submitOrderFeedback: (orderId: string, feedback: OrderFeedback) => void;
  oneClickReorder: (order: Order) => void;

  // Wallet & Favorites
  topUpWallet: (amount: number) => void;
  toggleFavorite: (itemId: string) => void;

  // Notifications
  notifications: AppNotification[];
  markNotificationRead: (id: string) => void;
  clearAllNotifications: () => void;

  // Simulation & Queue Info
  autoSimulateKitchen: boolean;
  setAutoSimulateKitchen: (enabled: boolean) => void;
  queueStatus: {
    pendingCount: number;
    preparingCount: number;
    readyCount: number;
    estimatedWaitMinutes: number;
    currentServingToken: string;
  };
}

const AppContext = createContext<AppContextType | undefined>(undefined);

const STORAGE_KEYS = {
  ORDERS: 'campuseats_orders_v1',
  MENU: 'campuseats_menu_v1',
  INVENTORY: 'campuseats_inventory_v1',
  USER_WALLET: 'campuseats_wallet_v1',
  CANTEENS: 'campuseats_canteens_v1',
  FAVORITES: 'campuseats_favorites_v1',
  AUTO_SIM: 'campuseats_autosim_v1',
  USER: 'campuseats_user_v1',
};

export const AppProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  // Roles & Users
  const [currentRole, setRoleState] = useState<UserRole>(() => {
    const saved = localStorage.getItem('campuseats_user_v1');
    if (saved) {
      try {
        const u = JSON.parse(saved);
        if (u.role) return u.role;
      } catch (e) {}
    }
    return 'student';
  });
  const [availableUsers] = useState<UserProfile[]>(INITIAL_USERS);
  const [currentUser, setCurrentUserState] = useState<UserProfile>(() => {
    const saved = localStorage.getItem('campuseats_user_v1');
    if (saved) {
      try {
        const u = JSON.parse(saved);
        if (u && typeof u.name === 'string' && u.name.includes('Rahul')) {
          u.name = u.name.replace(/Rahul\s*Sharma/g, 'Namit').replace(/Rahul/g, 'Namit');
          if (u.email) u.email = u.email.replace(/rahul/gi, 'namit');
          localStorage.setItem('campuseats_user_v1', JSON.stringify(u));
        }
        return u;
      } catch (e) {}
    }
    return INITIAL_USERS[0];
  });

  // Canteens
  const [canteens, setCanteens] = useState<Canteen[]>(() => {
    const saved = localStorage.getItem(STORAGE_KEYS.CANTEENS);
    return saved ? JSON.parse(saved) : INITIAL_CANTEENS;
  });
  const [selectedCanteenId, setSelectedCanteenId] = useState<string>('canteen-main');

  const selectedCanteen = useMemo(() => {
    return canteens.find((c) => c.id === selectedCanteenId) || canteens[0];
  }, [canteens, selectedCanteenId]);

  // Menu & Inventory
  const [menuItems, setMenuItems] = useState<MenuItem[]>(() => {
    const saved = localStorage.getItem(STORAGE_KEYS.MENU);
    if (saved) {
      try {
        const parsed: MenuItem[] = JSON.parse(saved);
        if (Array.isArray(parsed)) {
          return parsed.map((item) => {
            const initial = INITIAL_MENU_ITEMS.find((m) => m.id === item.id);
            return {
              ...item,
              isVegan: item.isVegan ?? initial?.isVegan ?? false,
              isGlutenFree: item.isGlutenFree ?? initial?.isGlutenFree ?? false,
              isDairyFree: item.isDairyFree ?? initial?.isDairyFree ?? false,
              isHighProtein: item.isHighProtein ?? initial?.isHighProtein ?? false,
              dietaryTags: item.dietaryTags ?? initial?.dietaryTags ?? (item.isVeg ? ['veg'] : []),
            };
          });
        }
      } catch (e) {}
    }
    return INITIAL_MENU_ITEMS;
  });
  const [inventory, setInventory] = useState<InventoryItem[]>(() => {
    const saved = localStorage.getItem(STORAGE_KEYS.INVENTORY);
    return saved ? JSON.parse(saved) : INITIAL_INVENTORY;
  });

  // Slots
  const [pickupSlots] = useState<PickupSlot[]>(INITIAL_PICKUP_SLOTS);

  // Cart
  const [cart, setCart] = useState<CartItem[]>([]);

  // Orders
  const [orders, setOrders] = useState<Order[]>(() => {
    const saved = localStorage.getItem(STORAGE_KEYS.ORDERS);
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        if (Array.isArray(parsed)) {
          return parsed.map((o: Order) => ({
            ...o,
            userName: o.userName ? o.userName.replace(/Rahul\s*Sharma/g, 'Namit').replace(/Rahul/g, 'Namit') : o.userName,
          }));
        }
      } catch (e) {}
    }
    return INITIAL_ORDERS;
  });

  // Notifications
  const [notifications, setNotifications] = useState<AppNotification[]>([
    {
      id: 'notif-welcome',
      title: 'Welcome to CampusEats! ðŸš€',
      message: 'Skip canteen queues! Pre-order now and collect with your live digital token.',
      type: 'info',
      timestamp: 'Just now',
      read: false,
    },
  ]);

  // Demo auto-simulation switch
  const [autoSimulateKitchen, setAutoSimulateKitchenState] = useState<boolean>(false);

  // Load real canteen and menu data from backend
  useEffect(() => {
    const loadBackendData = async () => {
      try {
        const canteenData = await apiRequest("/canteens");

        if (canteenData.canteens?.length > 0) {
          setCanteens((prev) =>
            canteenData.canteens.map((backendCanteen: any, index: number) => {
              const existing = prev[index] || prev[0];

              return {
                ...existing,
                id: String(backendCanteen.id),
                name: backendCanteen.name,
                location: backendCanteen.location || existing?.location || "",
                isActive: Boolean(backendCanteen.is_active),
              };
            })
          );

          setSelectedCanteenId(String(canteenData.canteens[0].id));
        }

        const firstCanteenId = canteenData.canteens?.[0]?.id;

        if (firstCanteenId) {
          const menuData = await apiRequest(`/menu/${firstCanteenId}`);

          if (menuData.items?.length > 0) {
            setMenuItems((prev) =>
              menuData.items.map((backendItem: any) => {
                const cleanBackendName = String(backendItem.name || '').trim().toLowerCase();
                const existing = prev.find((item) => {
                  const cleanItemName = item.name.trim().toLowerCase();
                  return (
                    cleanItemName === cleanBackendName ||
                    cleanItemName.includes(cleanBackendName) ||
                    cleanBackendName.includes(cleanItemName)
                  );
                });

                const categoryMap: Record<string, MenuItem["category"]> = {
                  breakfast: "breakfast",
                  meals: "meals",
                  "meals & bowls": "meals",
                  snacks: "snacks",
                  beverages: "drinks",
                  drinks: "drinks",
                  combos: "combos",
                };

                const backendCategory = String(
                  backendItem.category || "snacks"
                ).toLowerCase();

                const resolvedCategory =
                  categoryMap[backendCategory] ||
                  existing?.category ||
                  "snacks";

                const resolvedImage = getFoodImage(
                  backendItem.name,
                  resolvedCategory,
                  backendItem.image_url || existing?.image
                );

                return {
                  ...existing,
                  id: String(backendItem.id),
                  canteenId: String(backendItem.canteen_id),
                  name: backendItem.name,
                  description:
                    backendItem.description ||
                    existing?.description ||
                    "",
                  price: Number(backendItem.price),
                  category: resolvedCategory,
                  isVeg: existing?.isVeg ?? (backendItem.is_veg ?? true),
                  isVegan: existing?.isVegan ?? (backendItem.is_vegan ?? false),
                  isGlutenFree: existing?.isGlutenFree ?? (backendItem.is_gluten_free ?? false),
                  isDairyFree: existing?.isDairyFree ?? false,
                  isHighProtein: existing?.isHighProtein ?? false,
                  dietaryTags: existing?.dietaryTags ?? backendItem.dietary_tags ?? (existing?.isVeg ? ['veg'] : []),
                  rating: existing?.rating ?? 4.5,
                  ratingCount: existing?.ratingCount ?? 0,
                  prepTimeMinutes:
                    existing?.prepTimeMinutes ?? 10,
                  inStock: Boolean(backendItem.is_available),
                  stockQuantity: existing?.stockQuantity ?? 100,
                  maxStock: existing?.maxStock ?? 100,
                  image: resolvedImage,
                  isPopular: existing?.isPopular ?? false,
                  isOffer: existing?.isOffer ?? false,
                  offerTag: existing?.offerTag,
                  calories: existing?.calories,
                  customizations: existing?.customizations,
                };
              })
            );
          }
        }
      } catch (error) {
        console.warn("Backend canteen/menu API unreachable, using local data fallback:", error);
      }
    };

    loadBackendData();
  }, []);
  // Fetch /auth/me on mount if token exists to ensure currentUser and role match MySQL
  useEffect(() => {
    const token = localStorage.getItem("token");
    if (!token) return;

    const syncUserProfile = async () => {
      try {
        const data = await apiRequest("/auth/me");
        if (data.success && data.user) {
          const u = data.user;
          const userProfile: UserProfile = {
            id: String(u.id),
            name: u.name,
            studentId: `STU-${u.id}`,
            department: "Campus",
            year: "Member",
            phone: "",
            email: u.email,
            walletBalance: Number(u.wallet_balance ?? 0),
            role: u.role,
            favoriteItemIds: [],
          };
          setCurrentUserState(userProfile);
          setRoleState(u.role);
          localStorage.setItem(STORAGE_KEYS.USER, JSON.stringify(userProfile));
        }
      } catch (err) {
        console.warn("Failed to sync /auth/me:", err);
      }
    };

    syncUserProfile();
  }, []);

  // Load authenticated user's real orders from backend
  useEffect(() => {
    const token = localStorage.getItem("token");

    if (!token || !currentUser?.id) return;

    // Student orders should not overwrite Kitchen/Admin/Counter orders
    const isRestrictedRole =
      ["kitchen", "counter", "admin"].includes(String(currentUser.role).toLowerCase()) ||
      ["kitchen", "counter", "admin"].includes(String(currentRole).toLowerCase());

    if (isRestrictedRole) {
      return;
    }

    const loadMyOrders = async () => {
      try {
        const data = await apiRequest("/orders/my-orders");

        if (!data.success || !Array.isArray(data.orders)) {
          return;
        }

        const statusMap: Record<string, OrderStatus> = {
          placed: "CONFIRMED",
          accepted: "ACCEPTED",
          preparing: "PREPARING",
          ready: "READY",
          completed: "COLLECTED",
          cancelled: "CANCELLED",
        };

        setOrders((prev) => {
          const previousOrders = new Map<string, Order>(
            prev.map((order) => [String(order.id), order])
          );

          const backendOrders: Order[] = data.orders.map((backendOrder: any) => {
            const existing = previousOrders.get(String(backendOrder.id));

            return {
              id: String(backendOrder.id),
              tokenNumber: String(backendOrder.token_number),
              userId: String(currentUser.id),
              userName: currentUser.name,
              userRole: currentUser.role as any,

              canteenId: String(backendOrder.canteen_id),
              canteenName: backendOrder.canteen_name,

              items: (backendOrder.items && backendOrder.items.length > 0)
                ? backendOrder.items.map((it: any) => ({
                    id: String(it.menu_item_id || it.id),
                    name: it.name || "Item",
                    price: Number(it.price || 0),
                    quantity: Number(it.quantity || 1),
                    isVeg: Boolean(it.is_veg ?? true),
                    customizationText: it.customization || undefined,
                  }))
                : (existing?.items || []),

              subtotal: Number(backendOrder.total_amount),
              discount: 0,
              taxes: 0,
              total: Number(backendOrder.total_amount),

              paymentMethod: backendOrder.payment_method,
              paymentTransactionId:
                backendOrder.payment_transaction_id || undefined,
              paymentStatus:
                String(
                  backendOrder.payment_status || "pending"
                ).toUpperCase() as any,

              status:
                statusMap[String(backendOrder.status).toLowerCase()] ||
                "CONFIRMED",

              pickupSlot: existing?.pickupSlot || "",
              pickupCounter:
                existing?.pickupCounter || "Pickup Counter 1",
              estimatedReadyTime:
                existing?.estimatedReadyTime || "",
              estimatedPrepMinutes:
                existing?.estimatedPrepMinutes || 10,

              createdAt:
                backendOrder.created_at || existing?.createdAt || new Date().toISOString(),
              updatedAt: new Date().toISOString(),

              feedback: existing?.feedback,
            };
          });

          return backendOrders;
        });

        console.log(
          `Loaded ${data.orders.length} real orders from backend`
        );
      } catch (error) {
        console.warn("Real orders sync note (using local cache):", error);
      }
    };

    loadMyOrders();
  }, [currentUser?.id, currentUser?.role, currentRole]);

  // Load real kitchen orders from backend
  useEffect(() => {
    const token = localStorage.getItem("token");

    if (!token || !currentUser?.id) return;

    const isKitchenOrAdmin =
      ["kitchen", "admin"].includes(String(currentUser.role).toLowerCase()) ||
      ["kitchen", "admin"].includes(String(currentRole).toLowerCase());
    const isCounter =
      String(currentUser.role).toLowerCase() === "counter" ||
      String(currentRole).toLowerCase() === "counter";

    if (!isKitchenOrAdmin && !isCounter) {
      return;
    }

    const loadStaffOrders = async () => {
      try {
        const endpoint = isCounter ? "/counter/orders" : "/kitchen/orders";
        const data = await apiRequest(endpoint);

        if (!data.success || !Array.isArray(data.orders)) {
          console.warn("Unexpected staff orders response:", data);
          return;
        }

        const statusMap: Record<string, OrderStatus> = {
          placed: "CONFIRMED",
          accepted: "ACCEPTED",
          preparing: "PREPARING",
          ready: "READY",
          completed: "COLLECTED",
          cancelled: "CANCELLED",
        };

        setOrders((prev) => {
          const previousOrders = new Map<string, Order>(
            prev.map((order) => [String(order.id), order])
          );

          return data.orders.map((backendOrder: any) => {
            const existing = previousOrders.get(String(backendOrder.id));

            return {
              id: String(backendOrder.id),
              tokenNumber: String(backendOrder.token_number),
              userId: String(backendOrder.user_id),
              userName: backendOrder.student_name || "Student",
              userRole: "student",

              canteenId: String(backendOrder.canteen_id),
              canteenName: backendOrder.canteen_name,

              items: (backendOrder.items && backendOrder.items.length > 0)
                ? backendOrder.items.map((it: any) => ({
                    id: String(it.menu_item_id || it.id),
                    name: it.name,
                    price: Number(it.price),
                    quantity: Number(it.quantity),
                    isVeg: Boolean(it.is_veg ?? true),
                    customizationText: it.customization || undefined,
                  }))
                : (existing?.items || []),

              subtotal: Number(backendOrder.total_amount),
              discount: 0,
              taxes: 0,
              total: Number(backendOrder.total_amount),

              paymentMethod: backendOrder.payment_method || existing?.paymentMethod || "wallet",
              paymentTransactionId:
                backendOrder.payment_transaction_id || existing?.paymentTransactionId,

              paymentStatus:
                String(backendOrder.payment_status || existing?.paymentStatus || "PAID").toUpperCase() as any,

              status:
                statusMap[String(backendOrder.status).toLowerCase()] ||
                "CONFIRMED",

              pickupSlot: existing?.pickupSlot || "Immediate",
              pickupCounter:
                existing?.pickupCounter || "Pickup Counter 1",

              estimatedReadyTime:
                existing?.estimatedReadyTime || "",

              estimatedPrepMinutes:
                existing?.estimatedPrepMinutes || 10,

              createdAt:
                backendOrder.created_at ||
                existing?.createdAt ||
                new Date().toISOString(),

              updatedAt: new Date().toISOString(),

              feedback: existing?.feedback,
            };
          });
        });

        console.log(
          `Loaded ${data.orders.length} real kitchen orders from backend`
        );
      } catch (error) {
        console.warn("Staff orders sync note (using local cache):", error);
      }
    };

    loadStaffOrders();
  }, [currentUser?.id, currentUser?.role, currentRole]);

  const socketRef = useRef<any>(null);

  // Real-time order status synchronization
  useEffect(() => {
    const token = localStorage.getItem("token");

    if (!token || !currentUser?.id) return;

    const wsEnvUrl = (import.meta.env.VITE_WS_URL as string | undefined)?.trim();
    const apiBase = getApiBaseUrl();
    const socketBase = wsEnvUrl || (apiBase.startsWith("http")
      ? apiBase.replace(/\/api\/?$/, "")
      : (typeof window !== "undefined" && window.location.hostname !== "localhost" && window.location.hostname !== "127.0.0.1")
      ? window.location.origin
      : "http://localhost:5000");

    const socket = io(socketBase, {
      transports: ["websocket", "polling"],
      auth: {
        token: token || undefined,
      },
      reconnectionAttempts: 2,
      timeout: 3000,
    });

    socketRef.current = socket;

    socket.on("connect_error", () => {
      // Gracefully silent connection errors
    });

    socket.on("connect", () => {
      console.log("CampusEats Socket.IO connected");

      const isStaff =
        ["kitchen", "counter", "admin"].includes(String(currentUser.role).toLowerCase()) ||
        ["kitchen", "counter", "admin"].includes(String(currentRole).toLowerCase());

      if (isStaff && selectedCanteen?.id) {
        socket.emit("joinCanteen", selectedCanteen.id);
        console.log(`Staff socket joined canteen room: canteen_${selectedCanteen.id}`);
      }

      orders
        .filter((order) =>
          ["CONFIRMED", "ACCEPTED", "PREPARING", "READY"].includes(order.status)
        )
        .forEach((order) => {
          socket.emit("joinOrder", order.id);
        });
    });

    socket.on("newOrderCreated", (data: any) => {
      console.log("New order created broadcast:", data);
      if (!data || !data.id) return;

      socket.emit("joinOrder", data.id);

      const isStaff =
        ["kitchen", "counter", "admin"].includes(String(currentUser.role).toLowerCase()) ||
        ["kitchen", "counter", "admin"].includes(String(currentRole).toLowerCase());

      if (isStaff) {
        try {
          playOrderPlacedSound();
        } catch (e) {}
      }

      setOrders((prev) => {
        if (prev.some((o) => Number(o.id) === Number(data.id))) {
          return prev;
        }

        const isMyOrder = String(data.user_id || data.userId) === String(currentUser.id);

        if (!isStaff && !isMyOrder) {
          return prev;
        }

        const newOrd: Order = {
          id: String(data.id),
          tokenNumber: String(data.token_number || data.tokenNumber),
          userId: String(data.user_id || data.userId),
          userName: data.student_name || data.userName || "Student",
          userRole: "student",
          canteenId: String(data.canteen_id || data.canteenId),
          canteenName: data.canteen_name || data.canteenName || selectedCanteen.name,
          items: Array.isArray(data.items)
            ? data.items.map((it: any) => ({
                id: String(it.menu_item_id || it.menuItemId || it.id),
                name: it.name || "Item",
                price: Number(it.price || 0),
                quantity: Number(it.quantity || 1),
                isVeg: true,
                customizationText: it.customization || undefined,
              }))
            : [],
          subtotal: Number(data.total_amount || data.totalAmount || 0),
          discount: 0,
          taxes: 0,
          total: Number(data.total_amount || data.totalAmount || 0),
          paymentMethod: data.payment_method || data.paymentMethod || "wallet",
          paymentTransactionId: data.payment_transaction_id || data.paymentTransactionId || undefined,
          paymentStatus: String(data.payment_status || data.paymentStatus || "PAID").toUpperCase() as any,
          status: "CONFIRMED",
          pickupSlot: "Immediate",
          pickupCounter: "Pickup Counter 1",
          estimatedReadyTime: "",
          estimatedPrepMinutes: 10,
          createdAt: data.created_at || data.createdAt || new Date().toISOString(),
          updatedAt: new Date().toISOString(),
        };

        return [newOrd, ...prev];
      });
    });

    socket.on(
      "orderStatusUpdated",
      (data: { orderId: number; status: string }) => {
        console.log("Live order status:", data);

        const statusMap: Record<string, OrderStatus> = {
          placed: "CONFIRMED",
          accepted: "ACCEPTED",
          preparing: "PREPARING",
          ready: "READY",
          completed: "COLLECTED",
          cancelled: "CANCELLED",
        };

        const newStatus =
          statusMap[String(data.status).toLowerCase()];

        if (!newStatus) return;

        if (newStatus === "READY") {
          playOrderReadyChime();
        }

        setOrders((prev) =>
          prev.map((order) =>
            Number(order.id) === Number(data.orderId)
              ? {
                  ...order,
                  status: newStatus,
                  updatedAt: new Date().toISOString(),
                }
              : order
          )
        );
      }
    );

    socket.on("disconnect", () => {
      console.log("CampusEats Socket.IO disconnected");
      socketRef.current = null;
    });

    return () => {
      socket.disconnect();
      socketRef.current = null;
    };
  }, [currentUser?.id, currentUser?.role, currentRole]);

  // Synchronize canteen room on active socket when selected canteen changes
  useEffect(() => {
    if (socketRef.current && selectedCanteen?.id) {
      const isStaff =
        ["kitchen", "counter", "admin"].includes(String(currentUser?.role).toLowerCase()) ||
        ["kitchen", "counter", "admin"].includes(String(currentRole).toLowerCase());

      if (isStaff) {
        socketRef.current.emit("joinCanteen", selectedCanteen.id);
        console.log(`Synchronized socket to canteen room: canteen_${selectedCanteen.id}`);
      }
    }
  }, [selectedCanteen?.id, currentUser?.role, currentRole]);

  // Persist key states
  useEffect(() => {
    localStorage.setItem(STORAGE_KEYS.ORDERS, JSON.stringify(orders));
  }, [orders]);

  useEffect(() => {
    localStorage.setItem(STORAGE_KEYS.MENU, JSON.stringify(menuItems));
  }, [menuItems]);

  useEffect(() => {
    localStorage.setItem(STORAGE_KEYS.INVENTORY, JSON.stringify(inventory));
  }, [inventory]);

  useEffect(() => {
    localStorage.setItem(STORAGE_KEYS.CANTEENS, JSON.stringify(canteens));
  }, [canteens]);

  const setAutoSimulateKitchen = (val: boolean) => {
    setAutoSimulateKitchenState(val);
    localStorage.setItem(STORAGE_KEYS.AUTO_SIM, JSON.stringify(val));
  };

  const selectCanteen = (id: string) => {
    setSelectedCanteenId(id);
  };

  const updateCanteen = (canteen: Canteen) => {
    setCanteens((prev) => prev.map((c) => (c.id === canteen.id ? canteen : c)));
  };

  const setRole = (role: UserRole) => {
    const authRole = (currentUser?.role || 'student').toLowerCase() as UserRole;
    
    // Only allow role transition if authorized by authenticated backend role
    if (authRole === 'admin') {
      setRoleState(role);
    } else if (authRole === role) {
      setRoleState(role);
    } else {
      console.warn(`[RBAC] Blocked unauthorized client role switch from '${authRole}' to '${role}'.`);
      setRoleState(authRole);
    }
  };

  const setCurrentUser = (user: UserProfile) => {
    if (user.id === currentUser.id) {
      setCurrentUserState(user);
      localStorage.setItem(STORAGE_KEYS.USER, JSON.stringify(user));
    } else {
      console.warn("[RBAC] Client-side persona switching is disabled for authenticated users.");
    }
  };

  const loginUser = async (email: string, password: string): Promise<UserProfile> => {
    try {
      const data = await apiRequest("/auth/login", {
        method: "POST",
        body: JSON.stringify({
          email,
          password,
        }),
      });

      localStorage.setItem("token", data.token);

      const backendUser = data.user;

      const user: UserProfile = {
        id: String(backendUser.id),
        name: backendUser.name,
        studentId: `STU-${backendUser.id}`,
        department: "Campus",
        year: "Member",
        phone: "",
        email: backendUser.email,
        walletBalance: Number(backendUser.wallet_balance ?? 0),
        role: backendUser.role,
        favoriteItemIds: backendUser.favoriteItemIds ?? [],
      };

      localStorage.setItem(STORAGE_KEYS.USER, JSON.stringify(user));
      setCurrentUserState(user);
      setRoleState(user.role);

      return user;
    } catch (apiErr: any) {
      const isConnectionError =
        apiErr.message?.includes("Unable to reach backend server") ||
        apiErr.message?.includes("Network request failed") ||
        apiErr.message?.includes("Failed to fetch") ||
        apiErr.message?.includes("status 405") ||
        apiErr.message?.includes("status 404") ||
        apiErr.message?.includes("NetworkError");

      if (isConnectionError) {
        // Safe offline/preview fallback when backend server is unreachable
        const matched = INITIAL_USERS.find(
          (u) => u.email.toLowerCase() === email.toLowerCase()
        );

        let mockRole: UserRole = 'student';
        let mockName = email.split('@')[0];

        if (email.toLowerCase().includes('kitchen')) {
          mockRole = 'kitchen';
          mockName = 'Chef Suresh (Kitchen)';
        } else if (email.toLowerCase().includes('counter')) {
          mockRole = 'counter';
          mockName = 'Ramesh (Counter)';
        } else if (email.toLowerCase().includes('admin')) {
          mockRole = 'admin';
          mockName = 'Dr. Rajesh Sharma (Admin)';
        } else if (email.toLowerCase().includes('faculty')) {
          mockRole = 'faculty';
          mockName = 'Dr. Meera Nair (Faculty)';
        }

        const fallbackUser: UserProfile = matched || {
          id: `usr-${Date.now()}`,
          name: mockName.charAt(0).toUpperCase() + mockName.slice(1),
          studentId: `STU-${Math.floor(1000 + Math.random() * 9000)}`,
          department: "Campus",
          year: "Active",
          phone: "+91 98765 43210",
          email,
          walletBalance: 450,
          role: mockRole,
          favoriteItemIds: ['item-dosa', 'item-coldcoffee'],
        };

        localStorage.setItem("token", `demo-token-${Date.now()}`);
        localStorage.setItem(STORAGE_KEYS.USER, JSON.stringify(fallbackUser));
        setCurrentUserState(fallbackUser);
        setRoleState(fallbackUser.role);

        return fallbackUser;
      }

      // If backend responded with real error (e.g. 401 Unauthorized, 400 Bad Request)
      throw apiErr;
    }
  };

  const registerUser = async (
    name: string,
    email: string,
    password: string
  ): Promise<UserProfile> => {
    try {
      await apiRequest("/auth/register", {
        method: "POST",
        body: JSON.stringify({
          name,
          email,
          password,
        }),
      });

      return await loginUser(email, password);
    } catch (apiErr: any) {
      const isConnectionError =
        apiErr.message?.includes("Unable to reach backend server") ||
        apiErr.message?.includes("Network request failed") ||
        apiErr.message?.includes("Failed to fetch") ||
        apiErr.message?.includes("status 405") ||
        apiErr.message?.includes("status 404") ||
        apiErr.message?.includes("NetworkError");

      if (isConnectionError) {
        const fallbackUser: UserProfile = {
          id: `usr-${Date.now()}`,
          name,
          studentId: `STU-${Math.floor(1000 + Math.random() * 9000)}`,
          department: "Campus",
          year: "Member",
          phone: "+91 98765 00000",
          email,
          walletBalance: 300,
          role: "student",
          favoriteItemIds: [],
        };

        localStorage.setItem("token", `demo-token-${Date.now()}`);
        localStorage.setItem(STORAGE_KEYS.USER, JSON.stringify(fallbackUser));
        setCurrentUserState(fallbackUser);
        setRoleState(fallbackUser.role);

        return fallbackUser;
      }

      throw apiErr;
    }
  };

  const logoutUser = () => {
    localStorage.removeItem("token");
    localStorage.removeItem(STORAGE_KEYS.USER);
    if (socketRef.current) {
      try {
        socketRef.current.disconnect();
      } catch (e) {}
      socketRef.current = null;
    }
    setCart([]);
    setCurrentUserState(INITIAL_USERS[0]);
    setRoleState("student");
    window.dispatchEvent(new Event("storage"));
  };
  // Add Notification helper
  const addNotification = useCallback((notif: Omit<AppNotification, 'id' | 'timestamp' | 'read'>) => {
    const newNotif: AppNotification = {
      ...notif,
      id: `notif-${Date.now()}-${Math.random().toString(36).substr(2, 4)}`,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      read: false,
    };
    setNotifications((prev) => [newNotif, ...prev]);
  }, []);

  // Cart Operations
  const addToCart = (menuItem: MenuItem, quantity = 1, customizations: Record<string, string> = {}) => {
    // Check stock
    if (!menuItem.inStock || menuItem.stockQuantity <= 0) {
      alert('Sorry, this item is currently out of stock!');
      return;
    }

    setCart((prev) => {
      // Create unique key based on item id and customizations
      const customKey = Object.entries(customizations)
        .sort()
        .map(([k, v]) => `${k}:${v}`)
        .join('|');
      const cartItemId = `${menuItem.id}-${customKey}`;

      const existingIndex = prev.findIndex((item) => item.cartItemId === cartItemId);

      // Compute customization extra price
      let extraPrice = 0;
      if (menuItem.customizations) {
        menuItem.customizations.forEach((group) => {
          const selectedChoice = customizations[group.name];
          if (selectedChoice) {
            const found = group.choices.find((c) => c.label === selectedChoice);
            if (found) extraPrice += found.extraPrice;
          }
        });
      }

      const unitPrice = menuItem.price + extraPrice;

      if (existingIndex > -1) {
        const next = [...prev];
        const newQty = next[existingIndex].quantity + quantity;
        next[existingIndex] = {
          ...next[existingIndex],
          quantity: newQty,
          totalPrice: newQty * unitPrice,
        };
        return next;
      }

      return [
        ...prev,
        {
          cartItemId,
          menuItem,
          quantity,
          selectedCustomizations: customizations,
          unitPrice,
          totalPrice: unitPrice * quantity,
        },
      ];
    });
  };

  const removeFromCart = (cartItemId: string) => {
    setCart((prev) => prev.filter((item) => item.cartItemId !== cartItemId));
  };

  const updateCartQuantity = (cartItemId: string, delta: number) => {
    setCart((prev) => {
      return prev
        .map((item) => {
          if (item.cartItemId === cartItemId) {
            const newQty = item.quantity + delta;
            if (newQty <= 0) return null;
            return {
              ...item,
              quantity: newQty,
              totalPrice: newQty * item.unitPrice,
            };
          }
          return item;
        })
        .filter(Boolean) as CartItem[];
    });
  };

  const clearCart = () => {
    setCart([]);
  };

  const cartCount = useMemo(() => {
    return cart.reduce((acc, curr) => acc + curr.quantity, 0);
  }, [cart]);

  const cartTotal = useMemo(() => {
    return cart.reduce((acc, curr) => acc + curr.totalPrice, 0);
  }, [cart]);

  // Orders and Smart Token Generator
  const generateSmartToken = (canteen: Canteen): string => {
    // Generate sequential or smart prefix like A138 or M-0903-138
    const existingTokens = orders
      .filter((o) => o.canteenId === canteen.id)
      .map((o) => {
        const num = parseInt(o.tokenNumber.replace(/\D/g, ''), 10);
        return isNaN(num) ? 100 : num;
      });

    const maxNum = existingTokens.length > 0 ? Math.max(...existingTokens) : 130;
    const nextNum = maxNum + 1;
    return `A${nextNum}`;
  };

  const placeOrder = async (
    pickupSlot: string,
    paymentMethod: 'upi' | 'wallet' | 'card' | 'cash'
  ): Promise<Order> => {
    if (cart.length === 0) {
      throw new Error('Cart is empty');
    }

    const isExplicitMock = import.meta.env.VITE_USE_MOCK === 'true';

    // 1. Explicit Mock Mode (VITE_USE_MOCK=true)
    if (isExplicitMock) {
      const subtotal = cartTotal;
      const discount = subtotal >= 100 ? 15 : 0;
      const taxes = 0;
      const total = subtotal - discount + taxes;

      if (paymentMethod === 'wallet' && currentUser.walletBalance < total) {
        throw new Error('Insufficient wallet balance. Please top up your wallet or choose UPI/Cash.');
      }

      const tokenPrefix = selectedCanteen.code || 'A';
      const tokenNumber = `${tokenPrefix}${Math.floor(100 + Math.random() * 900)}`;
      const orderId = `CE${Date.now().toString().slice(-6)}`;

      const maxItemPrep = Math.max(...cart.map((c) => c.menuItem.prepTimeMinutes || 5));
      const activeQueueOrders = orders.filter(
        (o) => o.canteenId === selectedCanteen.id && ['CONFIRMED', 'ACCEPTED', 'PREPARING'].includes(o.status)
      ).length;
      const estimatedPrepMinutes = maxItemPrep + Math.round(activeQueueOrders * 1.5);
      const readyDate = new Date(Date.now() + estimatedPrepMinutes * 60 * 1000);
      const estimatedReadyTime = readyDate.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
      const pickupCounter = selectedCanteen.counters[0] || 'Pickup Counter 1';

      const localOrder: Order = {
        id: orderId,
        tokenNumber,
        userId: currentUser.id,
        userName: currentUser.name,
        userRole: currentUser.role,
        canteenId: selectedCanteen.id,
        canteenName: selectedCanteen.name,
        items: cart.map((item) => ({
          id: item.menuItem.id,
          name: item.menuItem.name,
          price: item.unitPrice,
          quantity: item.quantity,
          isVeg: item.menuItem.isVeg,
          customizationText:
            Object.entries(item.selectedCustomizations)
              .map(([_, val]) => val)
              .join(', ') || undefined,
        })),
        subtotal,
        discount,
        taxes,
        total,
        paymentMethod,
        paymentTransactionId: `TXN-LOCAL-${Date.now().toString().slice(-6)}`,
        paymentStatus: paymentMethod === 'cash' ? 'PENDING' : 'PAID',
        status: 'CONFIRMED',
        pickupSlot,
        pickupCounter,
        estimatedReadyTime,
        estimatedPrepMinutes,
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      };

      if (paymentMethod === 'wallet') {
        setCurrentUserState((prev) => ({
          ...prev,
          walletBalance: Math.max(0, prev.walletBalance - total),
        }));
      }

      setOrders((prev) => [localOrder, ...prev]);

      setMenuItems((prev) =>
        prev.map((menuItem) => {
          const cartItem = cart.find((item) => item.menuItem.id === menuItem.id);
          if (!cartItem) return menuItem;
          const newStock = Math.max(0, menuItem.stockQuantity - cartItem.quantity);
          return {
            ...menuItem,
            stockQuantity: newStock,
            inStock: newStock > 0,
          };
        })
      );

      clearCart();
      playOrderPlacedSound();

      addNotification({
        title: `Order Placed: Token ${tokenNumber} 🎉`,
        message: `Your order #${orderId} is confirmed at ${selectedCanteen.name}. Estimated Ready: ${estimatedReadyTime}`,
        tokenNumber,
        type: 'order_confirmed',
      });

      return localOrder;
    }

    // 2. Real Backend Order Flow (VITE_USE_MOCK=false) - Backend is the sole source of truth
    const canteenId = Number(selectedCanteen.id);

    const items = cart.map((item) => {
      const extraAmount = Math.max(
        0,
        Number(item.unitPrice) - Number(item.menuItem.price)
      );

      const customization =
        Object.entries(item.selectedCustomizations)
          .map(([key, value]) => `${key}: ${value}`)
          .join(' • ') || null;

      return {
        menuItemId: Number(item.menuItem.id),
        quantity: item.quantity,
        extraAmount,
        customization,
      };
    });

    const data = await apiRequest('/orders', {
      method: 'POST',
      body: JSON.stringify({
        canteenId,
        items,
        paymentMethod,
      }),
    });

    if (!data.success || !data.order) {
      throw new Error(data.message || 'Failed to place order');
    }

    const backendOrder = data.order;

    const subtotal = backendOrder.subtotal !== undefined ? Number(backendOrder.subtotal) : cartTotal;
    const discount = backendOrder.discount !== undefined ? Number(backendOrder.discount) : (subtotal >= 100 ? 15 : 0);
    const taxes = backendOrder.taxes !== undefined ? Number(backendOrder.taxes) : 0;
    const total = Number(backendOrder.totalAmount);

    const maxItemPrep = Math.max(
      ...cart.map((c) => c.menuItem.prepTimeMinutes || 5)
    );

    const activeQueueOrders = orders.filter(
      (o) =>
        o.canteenId === selectedCanteen.id &&
        ['CONFIRMED', 'ACCEPTED', 'PREPARING'].includes(o.status)
    ).length;

    const estimatedPrepMinutes =
      maxItemPrep + Math.round(activeQueueOrders * 1.5);

    const readyDate = new Date(
      Date.now() + estimatedPrepMinutes * 60 * 1000
    );

    const estimatedReadyTime = readyDate.toLocaleTimeString([], {
      hour: '2-digit',
      minute: '2-digit',
    });

    const pickupCounter =
      selectedCanteen.counters[
        Math.floor(
          Math.random() * Math.min(2, selectedCanteen.counters.length)
        )
      ] || 'Pickup Counter 1';

    const statusMap: Record<string, OrderStatus> = {
      placed: 'CONFIRMED',
      accepted: 'ACCEPTED',
      preparing: 'PREPARING',
      ready: 'READY',
      completed: 'COLLECTED',
      cancelled: 'CANCELLED',
    };

    const frontendStatus =
      statusMap[String(backendOrder.status).toLowerCase()] || 'CONFIRMED';

    const newOrder: Order = {
      id: String(backendOrder.id),
      tokenNumber: String(backendOrder.tokenNumber || backendOrder.token_number),
      userId: currentUser.id,
      userName: currentUser.name,
      userRole: currentUser.role,
      canteenId: selectedCanteen.id,
      canteenName: selectedCanteen.name,

      items: cart.map((item) => ({
        id: item.menuItem.id,
        name: item.menuItem.name,
        price: item.unitPrice,
        quantity: item.quantity,
        isVeg: item.menuItem.isVeg,
        customizationText:
          Object.entries(item.selectedCustomizations)
            .map(([_, value]) => value)
            .join(', ') || undefined,
      })),

      subtotal,
      discount,
      taxes,
      total,

      paymentMethod: backendOrder.paymentMethod || paymentMethod,
      paymentTransactionId:
        backendOrder.paymentTransactionId || backendOrder.payment_transaction_id || undefined,
      paymentStatus:
        String(backendOrder.paymentStatus || backendOrder.payment_status || 'paid').toLowerCase() === 'pending'
          ? 'PENDING'
          : 'PAID',

      status: frontendStatus,

      pickupSlot,
      pickupCounter,
      estimatedReadyTime,
      estimatedPrepMinutes,

      createdAt: backendOrder.created_at || new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };

    if (data.walletBalance !== null && data.walletBalance !== undefined) {
      setCurrentUserState((prev) => ({
        ...prev,
        walletBalance: Number(data.walletBalance),
      }));
    }

    setOrders((prev) => [newOrder, ...prev]);

    // Join socket room for live status updates
    socketRef.current?.emit("joinOrder", backendOrder.id);

    setMenuItems((prev) =>
      prev.map((menuItem) => {
        const cartItem = cart.find(
          (item) => item.menuItem.id === menuItem.id
        );

        if (!cartItem) return menuItem;

        const newStock = Math.max(
          0,
          menuItem.stockQuantity - cartItem.quantity
        );

        return {
          ...menuItem,
          stockQuantity: newStock,
          inStock: newStock > 0,
        };
      })
    );

    clearCart();

    playOrderPlacedSound();

    addNotification({
      title: `Order Placed: Token ${newOrder.tokenNumber} 🎉`,
      message: `Your order #${newOrder.id} is confirmed at ${selectedCanteen.name}. Estimated Ready: ${estimatedReadyTime}`,
      tokenNumber: newOrder.tokenNumber,
      type: 'order_confirmed',
    });

    return newOrder;
  };

  const cancelOrder = (orderId: string): boolean => {
    const order = orders.find((o) => o.id === orderId);
    if (!order) return false;

    // Call backend cancellation endpoint
    apiRequest(`/orders/${orderId}/cancel`, { method: "PATCH" })
      .then((data) => {
        setOrders((prev) =>
          prev.map((o) =>
            o.id === orderId
              ? { ...o, status: "CANCELLED", updatedAt: new Date().toISOString() }
              : o
          )
        );

        if (data.walletBalance !== null && data.walletBalance !== undefined) {
          setCurrentUserState((prev) => ({
            ...prev,
            walletBalance: Number(data.walletBalance),
          }));
        }

        addNotification({
          title: `Order #${order.id} Cancelled`,
          message: data.refundProcessed
            ? `Your order #${order.id} (Token ${order.tokenNumber}) has been cancelled. Payment of ₹${order.total} is refunded to wallet.`
            : `Your order #${order.id} (Token ${order.tokenNumber}) has been cancelled.`,
          tokenNumber: order.tokenNumber,
          type: 'cancelled',
        });
      })
      .catch((err) => {
        console.error("Cancel order error:", err);
        alert(err.message || "Unable to cancel order");
      });

    return true;
  };

  const updateOrderStatus = async (orderId: string, newStatus: OrderStatus) => {
    const backendStatusMap: Record<string, string> = {
      CONFIRMED: "placed",
      ACCEPTED: "accepted",
      PREPARING: "preparing",
      READY: "ready",
      COLLECTED: "completed",
      CANCELLED: "cancelled",
    };

    const frontendStatusMap: Record<string, OrderStatus> = {
      placed: "CONFIRMED",
      accepted: "ACCEPTED",
      preparing: "PREPARING",
      ready: "READY",
      completed: "COLLECTED",
      cancelled: "CANCELLED",
    };

    const backendStatus = backendStatusMap[newStatus];

    if (!backendStatus) {
      console.error("Invalid order status:", newStatus);
      return;
    }

    const currentOrder = orders.find((o) => String(o.id) === String(orderId));

    console.log(`[updateOrderStatus] Initiating PATCH /kitchen/orders/${orderId}/status:`, {
      orderId,
      requestedStatus: newStatus,
      backendStatus,
      currentOrderLocalStatus: currentOrder?.status,
      orderCanteenId: currentOrder?.canteenId,
      authenticatedUserId: currentUser?.id,
      authenticatedUserRole: currentUser?.role,
      authenticatedUserCanteenId: (currentUser as any)?.canteen_id,
    });

    try {
      const data = await apiRequest(`/kitchen/orders/${orderId}/status`, {
        method: "PATCH",
        body: JSON.stringify({
          status: backendStatus,
        }),
      });

      console.log(`[updateOrderStatus] Backend response:`, data);

      if (!data.success) {
        alert(data.message || "Failed to update order status");
        return;
      }

      const effectiveStatus = data.status
        ? (frontendStatusMap[String(data.status).toLowerCase()] || newStatus)
        : newStatus;

      setOrders((prev) =>
        prev.map((o) => {
          if (String(o.id) === String(orderId)) {
            return {
              ...o,
              status: effectiveStatus,
              updatedAt: new Date().toISOString(),
            };
          }
          return o;
        })
      );

      const order = orders.find((o) => String(o.id) === String(orderId));
      if (!order) return;

      if (effectiveStatus === "PREPARING") {
        addNotification({
          title: `Kitchen Preparing: Token ${order.tokenNumber} 👨‍🍳`,
          message: `Your food is now being prepared at ${order.canteenName}.`,
          tokenNumber: order.tokenNumber,
        });
      } else if (effectiveStatus === "READY") {
        addNotification({
          title: `Order Ready: Token ${order.tokenNumber} 🔔`,
          message: `Your order is ready for pickup at ${order.canteenName}.`,
          tokenNumber: order.tokenNumber,
        });
      } else if (effectiveStatus === "COLLECTED") {
        addNotification({
          title: `Order Collected: Token ${order.tokenNumber} ✅`,
          message: `Order ${order.tokenNumber} has been collected.`,
          tokenNumber: order.tokenNumber,
        });
      }
    } catch (error: any) {
      console.error(`[updateOrderStatus] Backend request failed:`, {
        httpStatus: error?.status,
        responseBody: error?.data,
        errorMessage: error?.message,
        orderId,
        requestedStatus: newStatus,
        backendStatus,
        currentDbStatus: error?.data?.currentStatus,
        authenticatedUserRole: currentUser?.role,
        authenticatedUserCanteenId: (currentUser as any)?.canteen_id,
        orderCanteenId: currentOrder?.canteenId,
      });

      // If backend reports the order is already in another state (stale frontend state), sync local state!
      if (error?.data?.currentStatus) {
        const dbStatus = String(error.data.currentStatus).toLowerCase();
        const syncedFrontendStatus = frontendStatusMap[dbStatus];
        if (syncedFrontendStatus) {
          console.log(`[updateOrderStatus] Synchronizing stale local order #${orderId} state to DB status: ${dbStatus} (${syncedFrontendStatus})`);
          setOrders((prev) =>
            prev.map((o) =>
              String(o.id) === String(orderId)
                ? { ...o, status: syncedFrontendStatus, updatedAt: new Date().toISOString() }
                : o
            )
          );
        }
      }

      // Display the REAL backend message instead of a generic alert
      const messageToDisplay = error?.data?.message || error?.message || "Failed to update order status";
      alert(messageToDisplay);
    }
  };

  // Call token from pickup counter with voice announcement!
  const callToken = (orderId: string) => {
    const order = orders.find((o) => o.id === orderId);
    if (!order) return;

    announceTokenVoice(order.tokenNumber, order.pickupCounter);

    addNotification({
      title: `ðŸ”Š Calling Token ${order.tokenNumber}`,
      message: `Announcement made for ${order.pickupCounter}!`,
      tokenNumber: order.tokenNumber,
      type: 'reminder',
    });
  };

  // Counter staff verifies QR or Token
  const verifyAndCollectOrder = async (
    tokenOrId: string
  ): Promise<{ success: boolean; message: string; order?: Order }> => {
    const cleanQuery = tokenOrId.trim().toUpperCase();
    const order = orders.find(
      (o) =>
        o.tokenNumber.toUpperCase() === cleanQuery ||
        o.id.toUpperCase() === cleanQuery ||
        o.id.toUpperCase() === `CE${cleanQuery}`
    );

    if (!order) {
      return {
        success: false,
        message: `Token or Order "${tokenOrId}" not found in current canteen queue.`,
      };
    }

    if (order.status === 'COLLECTED') {
      return {
        success: false,
        message: `Token ${order.tokenNumber} has already been collected!`,
        order,
      };
    }

    try {
      // Call dedicated counter collection endpoint only
      const data = await apiRequest(`/counter/orders/${order.id}/collect`, {
        method: "PATCH",
      });

      if (!data.success && data.message) {
        return { success: false, message: data.message, order };
      }
    } catch (err: any) {
      console.warn("Counter API collection fallback:", err?.message || err);
    }

    // Update local state to COLLECTED
    setOrders((prev) =>
      prev.map((o) => {
        if (o.id === order.id) {
          return {
            ...o,
            status: 'COLLECTED' as OrderStatus,
            updatedAt: new Date().toISOString(),
          };
        }
        return o;
      })
    );

    addNotification({
      title: `Order Collected: Token ${order.tokenNumber} ✅`,
      message: `Order ${order.tokenNumber} has been verified and collected at ${order.canteenName}.`,
      tokenNumber: order.tokenNumber,
      type: 'info',
    });

    const updatedOrder: Order = {
      ...order,
      status: 'COLLECTED',
      updatedAt: new Date().toISOString(),
    };

    return {
      success: true,
      message: `Success! Token ${order.tokenNumber} verified & food collected.`,
      order: updatedOrder,
    };
  };

  const submitOrderFeedback = (orderId: string, feedback: OrderFeedback) => {
    apiRequest('/ratings', {
      method: 'POST',
      body: JSON.stringify({
        orderId: Number(orderId),
        rating: feedback.rating,
        review: feedback.comment || (feedback.issueReported ? `[Tag: ${feedback.issueReported}]` : null),
      }),
    }).catch((err) => {
      console.warn("Rating API warning:", err);
    });

    setOrders((prev) =>
      prev.map((o) => (o.id === orderId ? { ...o, feedback } : o))
    );
    addNotification({
      title: 'Thank you for your rating! â­',
      message: 'Your feedback helps improve canteen quality and prep speed.',
      type: 'info',
    });
  };

  const oneClickReorder = (pastOrder: Order) => {
    clearCart();
    let addedCount = 0;
    pastOrder.items.forEach((item) => {
      const menuItem = menuItems.find((m) => m.id === item.id);
      if (menuItem && menuItem.inStock) {
        addToCart(menuItem, item.quantity);
        addedCount++;
      }
    });
    if (addedCount > 0) {
      addNotification({
        title: 'Items Added to Cart! ðŸ›’',
        message: `Reordered ${addedCount} items from Order #${pastOrder.id}. Review and choose pickup slot.`,
        type: 'info',
      });
    } else {
      alert('Items from this order are currently unavailable or out of stock.');
    }
  };

  const topUpWallet = (amount: number) => {
    apiRequest('/wallet/add-money', {
      method: 'POST',
      body: JSON.stringify({ amount }),
    })
      .then((data) => {
        if (data.walletBalance !== undefined) {
          setCurrentUserState((prev) => ({
            ...prev,
            walletBalance: Number(data.walletBalance),
          }));
        }
        addNotification({
          title: `Wallet Credited: +₹${amount}`,
          message: `Your Campus Wallet balance is now ₹${data.walletBalance}.`,
          type: 'info',
        });
      })
      .catch((err) => {
        console.error("Top-up wallet error:", err);
        alert(err.message || "Failed to add money to wallet");
      });
  };

  const toggleFavorite = (itemId: string) => {
    setCurrentUserState((prev) => {
      const isFav = prev.favoriteItemIds.includes(itemId);
      const nextFavs = isFav
        ? prev.favoriteItemIds.filter((id) => id !== itemId)
        : [...prev.favoriteItemIds, itemId];
      return { ...prev, favoriteItemIds: nextFavs };
    });
  };

  const updateMenuItem = (item: MenuItem) => {
    setMenuItems((prev) => prev.map((m) => (m.id === item.id ? item : m)));
  };

  const addMenuItem = (item: Omit<MenuItem, 'id'>) => {
    const newItem: MenuItem = {
      ...item,
      id: `item-${Date.now()}`,
    };
    setMenuItems((prev) => [newItem, ...prev]);
  };

  const updateInventoryStock = async (itemId: string, newStock: number) => {
    setInventory((prev) =>
      prev.map((inv) => (inv.id === itemId ? { ...inv, currentStock: newStock } : inv))
    );

    // Persist to backend if numeric ID
    const numericId = Number(itemId.replace(/^item-/, ""));
    if (!isNaN(numericId) && numericId > 0) {
      try {
        await apiRequest(`/menu/${numericId}/stock`, {
          method: "PATCH",
          body: JSON.stringify({
            stockQuantity: newStock,
            isTracked: true,
            isAvailable: newStock > 0,
          }),
        });
      } catch (err) {
        console.warn("Backend stock sync notice:", err);
      }
    }
  };

  const restockItem = async (itemId: string, addAmount: number) => {
    let updatedStock = addAmount;
    setInventory((prev) =>
      prev.map((inv) => {
        if (inv.id === itemId) {
          const updated = Math.min(inv.maxStock, inv.currentStock + addAmount);
          updatedStock = updated;
          return { ...inv, currentStock: updated };
        }
        return inv;
      })
    );

    const numericId = Number(itemId.replace(/^item-/, ""));
    if (!isNaN(numericId) && numericId > 0) {
      try {
        await apiRequest(`/menu/${numericId}/stock`, {
          method: "PATCH",
          body: JSON.stringify({
            stockQuantity: updatedStock,
            isTracked: true,
            isAvailable: true,
          }),
        });
      } catch (err) {
        console.warn("Backend restock sync notice:", err);
      }
    }

    addNotification({
      title: 'Inventory Restocked 📦',
      message: `Added +${addAmount} units to stock.`,
      type: 'info',
    });
  };

  const markNotificationRead = (id: string) => {
    setNotifications((prev) => prev.map((n) => (n.id === id ? { ...n, read: true } : n)));
  };

  const clearAllNotifications = () => {
    setNotifications([]);
  };

  // Active student orders (orders in active status for current student)
  const activeOrders = useMemo(() => {
    if (!orders || !currentUser) return [];
    return orders.filter(
      (o) =>
        o.userId === currentUser.id &&
        ['CONFIRMED', 'ACCEPTED', 'PREPARING', 'READY'].includes(o.status)
    );
  }, [orders, currentUser]);

  // Active student order (most recent active order for current student)
  const activeOrder = useMemo(() => {
    return activeOrders[0] || null;
  }, [activeOrders]);

  // Real-time Queue Status metrics
  const queueStatus = useMemo(() => {
    const canteenOrders = orders.filter((o) => o.canteenId === selectedCanteen.id);
    const pending = canteenOrders.filter((o) => o.status === 'CONFIRMED' || o.status === 'ACCEPTED').length;
    const preparing = canteenOrders.filter((o) => o.status === 'PREPARING').length;
    const ready = canteenOrders.filter((o) => o.status === 'READY').length;
    const estimatedWaitMinutes = selectedCanteen.waitTimeMinutes + Math.round((pending + preparing) * 1.5);

    return {
      pendingCount: pending,
      preparingCount: preparing,
      readyCount: ready,
      estimatedWaitMinutes,
      currentServingToken: selectedCanteen.currentServingToken,
    };
  }, [orders, selectedCanteen]);

  // Demo auto-simulation: Automatically advance orders for interactive demonstration
  useEffect(() => {
    if (!autoSimulateKitchen) return;

    const interval = setInterval(() => {
      // Find orders that need progression
      setOrders((currentOrders) => {
        let changed = false;
        const updated = currentOrders.map((ord) => {
          if (ord.status === 'CONFIRMED') {
            changed = true;
            return { ...ord, status: 'ACCEPTED' as OrderStatus, updatedAt: new Date().toISOString() };
          }
          return ord;
        });

        if (changed) return updated;
        return currentOrders;
      });
    }, 8000);

    return () => clearInterval(interval);
  }, [autoSimulateKitchen]);

  return (
    <AppContext.Provider
      value={{
        currentRole,
        setRole,
        currentUser,
        setCurrentUser,
        loginUser,
        registerUser,
        logoutUser,
        availableUsers,
        selectedCanteen,
        canteens,
        selectCanteen,
        updateCanteen,
        menuItems,
        updateMenuItem,
        addMenuItem,
        inventory,
        updateInventoryStock,
        restockItem,
        cart,
        cartCount,
        cartTotal,
        addToCart,
        removeFromCart,
        updateCartQuantity,
        clearCart,
        pickupSlots,
        orders,
        activeOrders,
        activeOrder,
        placeOrder,
        cancelOrder,
        updateOrderStatus,
        callToken,
        verifyAndCollectOrder,
        submitOrderFeedback,
        oneClickReorder,
        topUpWallet,
        toggleFavorite,
        notifications,
        markNotificationRead,
        clearAllNotifications,
        autoSimulateKitchen,
        setAutoSimulateKitchen,
        queueStatus,
      }}
    >
      {children}
    </AppContext.Provider>
  );
};

export const useApp = () => {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error('useApp must be used within an AppProvider');
  }
  return context;
};







