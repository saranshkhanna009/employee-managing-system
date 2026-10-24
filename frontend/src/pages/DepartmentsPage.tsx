import { Fragment, useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { Textarea } from '../components/ui/Textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/Select';
import { Card, CardContent } from '../components/ui/Card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../components/ui/Table';
import { Badge } from '../components/ui/Badge';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger, DropdownMenuSeparator } from '../components/ui/DropdownMenu';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogFooter, DialogClose } from '../components/ui/Dialog';
import { apiClient } from '../utils/api';
import { Department } from '../types';
import { useAuthStore } from '../store/auth';
import { Plus, Search, MoreVertical, Edit, Trash2, Loader2, ChevronRight, Building2 } from 'lucide-react';
import { toast } from 'sonner';

export function DepartmentsPage() {
  const queryClient = useQueryClient();
  const { hasRole } = useAuthStore();
  const isAdminOrAbove = hasRole('admin', 'super_admin');
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
  const [editingDepartment, setEditingDepartment] = useState<Department | null>(null);

  const [filters, setFilters] = useState({
    search: '',
    page: 1,
    page_size: 20,
  });

  const { data: departmentsData, isLoading } = useQuery({
    queryKey: ['departments', filters],
    queryFn: () => apiClient.getDepartments(filters),
  });

  const { data: allDepartments } = useQuery({
    queryKey: ['departments', 'all'],
    queryFn: () => apiClient.getDepartments({ page_size: 100 }),
    select: (res) => res.data.items,
  });

  const createMutation = useMutation({
    mutationFn: (data: { name: string; description?: string; parent_id?: string }) => apiClient.createDepartment(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['departments'] });
      setIsCreateDialogOpen(false);
      toast.success('Department created successfully');
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => apiClient.deleteDepartment(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['departments'] });
      toast.success('Department deleted');
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: { name: string; description?: string; parent_id?: string } }) =>
      apiClient.updateDepartment(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['departments'] });
      setEditingDepartment(null);
      toast.success('Department updated');
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const departments = departmentsData?.data.items || [];
  const total = departmentsData?.data.total || 0;

  // Build tree structure
  const buildTree = (depts: Department[], parentId: string | null = null): Department[] => {
    return depts
      .filter(d => d.parent_id === parentId)
      .map(d => ({
        ...d,
        children: buildTree(depts, d.id),
      }));
  };

  const tree = buildTree(departments);

  const renderDepartmentRow = (dept: Department, level: number = 0): JSX.Element => {
    const hasChildren = dept.children && dept.children.length > 0;
    const parentName = dept.parent_id ? departments.find((parent: Department) => parent.id === dept.parent_id)?.name : undefined;
    return (
      <Fragment key={dept.id}>
        <TableRow key={dept.id} style={{ paddingLeft: `${level * 20 + 12}px` }}>
          <TableCell className="font-medium">
            <div className="flex items-center gap-2">
              {hasChildren && (
                <ChevronRight className="h-4 w-4 text-muted-foreground transition-transform" />
              )}
              <Building2 className="h-4 w-4 text-muted-foreground" />
              <span>{dept.name}</span>
            </div>
          </TableCell>
          <TableCell>
            <p className="text-sm text-muted-foreground max-w-xs truncate">{dept.description || 'No description'}</p>
          </TableCell>
          <TableCell>
            <Badge variant="secondary">{dept.employees_count || 0}</Badge>
          </TableCell>
          <TableCell>
            <span className="text-sm text-muted-foreground">{parentName || 'Root'}</span>
          </TableCell>
          <TableCell className="text-right">
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" size="icon">
                  <MoreVertical className="h-4 w-4" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                  <DropdownMenuItem onClick={() => setEditingDepartment(dept)}>
                    View / Edit Details
                  </DropdownMenuItem>
                {isAdminOrAbove && (
                  <>
                    <DropdownMenuSeparator />
                    <DropdownMenuItem onClick={() => setEditingDepartment(dept)}>
                      <Edit className="mr-2 h-4 w-4" />
                      Edit
                    </DropdownMenuItem>
                    <DropdownMenuItem
                      onClick={() => {
                        if (confirm(`Are you sure you want to delete "${dept.name}"? This action cannot be undone.`)) {
                          deleteMutation.mutate(dept.id);
                        }
                      }}
                      className="text-destructive focus:text-destructive"
                    >
                      <Trash2 className="mr-2 h-4 w-4" />
                      Delete
                    </DropdownMenuItem>
                  </>
                )}
              </DropdownMenuContent>
            </DropdownMenu>
          </TableCell>
        </TableRow>
        {hasChildren && dept.children?.map(child => renderDepartmentRow(child, level + 1))}
      </Fragment>
    );
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Departments</h1>
          <p className="text-muted-foreground">Manage company departments and hierarchy</p>
        </div>
        {isAdminOrAbove && (
          <Dialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}>
            <DialogTrigger asChild>
              <Button>
                <Plus className="mr-2 h-4 w-4" />
                Add Department
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DepartmentForm onSubmit={createMutation.mutate} departments={allDepartments || []} />
            </DialogContent>
          </Dialog>
        )}
      </div>

      {/* Search */}
      <Card>
        <CardContent className="pt-6">
          <div className="relative max-w-md">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              placeholder="Search departments..."
              value={filters.search}
              onChange={(e) => setFilters({ ...filters, search: e.target.value, page: 1 })}
              className="pl-10"
            />
          </div>
        </CardContent>
      </Card>

      {/* Departments Table */}
      <Card>
        <CardContent>
          {isLoading ? (
            <div className="space-y-4">
              {[1, 2, 3, 4, 5].map((i) => (
                <div key={i} className="h-12 animate-pulse bg-muted rounded" />
              ))}
            </div>
          ) : (
            <>
              {departments.length > 0 ? (
                <div className="rounded-md border">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Department</TableHead>
                        <TableHead>Description</TableHead>
                        <TableHead>Employees</TableHead>
                        <TableHead>Parent</TableHead>
                        <TableHead className="text-right">Actions</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {tree.map(dept => renderDepartmentRow(dept))}
                    </TableBody>
                  </Table>
                </div>
              ) : (
                <div className="text-center py-12">
                  <Building2 className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
                  <h3 className="text-lg font-medium mb-2">No departments found</h3>
                  <p className="text-muted-foreground mb-4">Create your first department to get started.</p>
                  {isAdminOrAbove && (
                     <Button onClick={() => setIsCreateDialogOpen(true)}>
                      <Plus className="mr-2 h-4 w-4" />
                      Create Department
                    </Button>
                  )}
                </div>
              )}

              {/* Pagination */}
              {total > filters.page_size && (
                <div className="flex items-center justify-between mt-4">
                  <p className="text-sm text-muted-foreground">
                    Showing {(filters.page - 1) * filters.page_size + 1} to{' '}
                    {Math.min(filters.page * filters.page_size, total)} of {total} departments
                  </p>
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={filters.page === 1}
                      onClick={() => setFilters({ ...filters, page: filters.page - 1 })}
                    >
                      Previous
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={filters.page * filters.page_size >= total}
                      onClick={() => setFilters({ ...filters, page: filters.page + 1 })}
                    >
                      Next
                    </Button>
                  </div>
                </div>
              )}
            </>
          )}
        </CardContent>
      </Card>

      {editingDepartment && (
        <Dialog open onOpenChange={(open) => !open && setEditingDepartment(null)}>
          <DialogContent>
            <DepartmentForm
              initialData={editingDepartment}
              onSubmit={(data) => updateMutation.mutate({ id: editingDepartment.id, data })}
              departments={allDepartments || []}
            />
          </DialogContent>
        </Dialog>
      )}
    </div>
  );
}

interface DepartmentFormProps {
  onSubmit: (data: { name: string; description?: string; parent_id?: string }) => void;
  departments: Department[];
  initialData?: Department;
}

function DepartmentForm({ onSubmit, departments, initialData }: DepartmentFormProps) {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const isEditing = !!initialData;

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setIsSubmitting(true);
    const formData = new FormData(e.currentTarget);
    const parentId = formData.get('parent_id') as string;
    const data = {
      name: formData.get('name') as string,
      description: formData.get('description') as string || undefined,
      parent_id: parentId === '__none__' ? undefined : parentId || undefined,
    };
    await onSubmit(data);
    setIsSubmitting(false);
  };

  return (
    <form onSubmit={handleSubmit}>
      <DialogHeader>
        <DialogTitle>{isEditing ? 'Edit Department' : 'Create Department'}</DialogTitle>
      </DialogHeader>
      <div className="grid gap-4 py-4">
        <div className="grid gap-2">
          <label htmlFor="name" className="text-sm font-medium">Name *</label>
          <Input id="name" name="name" required defaultValue={initialData?.name || ''} placeholder="e.g., Engineering" />
        </div>
        <div className="grid gap-2">
          <label htmlFor="description" className="text-sm font-medium">Description</label>
          <Textarea id="description" name="description" defaultValue={initialData?.description || ''} placeholder="Department description..." rows={3} />
        </div>
        <div className="grid gap-2">
          <label htmlFor="parent_id" className="text-sm font-medium">Parent Department</label>
          <Select name="parent_id" defaultValue={initialData?.parent_id || '__none__'}>
            <SelectTrigger>
              <SelectValue placeholder="No parent (root level)" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="__none__">No parent (root level)</SelectItem>
              {departments
                .filter(d => d.id !== initialData?.id) // Prevent circular reference
                .map((dept) => (
                  <SelectItem key={dept.id} value={dept.id}>{dept.name}</SelectItem>
                ))}
            </SelectContent>
          </Select>
        </div>
      </div>
      <DialogFooter>
        <DialogClose asChild>
          <Button type="button" variant="outline">Cancel</Button>
        </DialogClose>
        <Button type="submit" disabled={isSubmitting}>
          {isSubmitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
          {isEditing ? 'Update Department' : 'Create Department'}
        </Button>
      </DialogFooter>
    </form>
  );
}
