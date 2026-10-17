export type Role = "donor" | "recipient" | "admin";

export type DonationStatus =
  | "open"
  | "partially_allocated"
  | "allocated"
  | "expired"
  | "cancelled";

export type InvitationStatus =
  | "pending"
  | "accepted"
  | "declined"
  | "cancelled"
  | "expired";

export type PickupStatus = "pending" | "confirmed" | "completed" | "failed";

export interface Donation {
  id: number;
  donor_name: string;
  category: string;
  food_name: string;
  total_portions: number;
  remaining_portions: number;
  pickup_deadline: string;
  pickup_address: string;
  notes?: string | null;
  status: DonationStatus;
  is_demo: boolean;
  invitations_created?: number;
}

export interface MatchOffer {
  invitation_id: number;
  recipient_id: number;
  suggested_portions: number;
  score: number;
  status: InvitationStatus;
  breakdown?: Record<string, unknown>;
  reasons?: string[];
}

export interface Invitation {
  id: number;
  donation_id: number;
  recipient_id: number;
  recipient_name?: string;
  suggested_portions: number;
  score: number;
  status: InvitationStatus;
  reasons?: string[];
  donation?: {
    id: number;
    donor_name: string;
    category: string;
    food_name: string;
    pickup_deadline: string;
    pickup_address: string;
    remaining_portions: number;
    status: string;
  };
}

export interface Allocation {
  id: number;
  donation_id: number;
  recipient_id: number;
  recipient_name?: string;
  portions: number;
  pickup_status: PickupStatus;
}

export interface AdminDashboard {
  label: string;
  total_donations: number;
  total_portions_donated: number;
  portions_remaining: number;
  portions_allocated: number;
  portions_pickup_confirmed: number;
  portions_pickup_completed: number;
  pending_invitations: number;
  declined_invitations: number;
  donations_needing_recovery: number;
  recovery_rate_percent: number;
  note: string;
}

export interface ExplainMatchResponse {
  donation_id: number;
  source: "gemini" | "fallback";
  summary: string;
  matches: MatchOffer[];
  suggested_actions: string[];
}
